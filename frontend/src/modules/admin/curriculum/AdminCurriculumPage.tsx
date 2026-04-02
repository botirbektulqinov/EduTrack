import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  FiArrowRight,
  FiBookOpen,
  FiRefreshCw,
  FiSave,
} from 'react-icons/fi';
import api from '@/lib/api';
import type {
  CurriculumModule,
  CurriculumReviewQueue,
  CurriculumSubject,
  CurriculumTopic,
  CurriculumTree,
} from '@/types';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';
import Input from '@/components/ui/Input';
import Spinner from '@/components/ui/Spinner';
import Textarea from '@/components/ui/Textarea';
import styles from './AdminCurriculumPage.module.scss';

interface SubjectDraft {
  id?: string;
  name: string;
  code: string;
  description: string;
}

interface ModuleDraft {
  id?: string;
  name: string;
  description: string;
  order_index: string;
}

interface TopicDraft {
  id?: string;
  name: string;
  description: string;
  order_index: string;
}

const EMPTY_SUBJECT: SubjectDraft = { name: '', code: '', description: '' };
const EMPTY_MODULE: ModuleDraft = { name: '', description: '', order_index: '0' };
const EMPTY_TOPIC: TopicDraft = { name: '', description: '', order_index: '0' };

function buildSubjectDraft(subject: CurriculumSubject | null): SubjectDraft {
  if (!subject) {
    return EMPTY_SUBJECT;
  }
  return {
    id: subject.id,
    name: subject.name,
    code: subject.code ?? '',
    description: subject.description ?? '',
  };
}

function buildModuleDraft(module: CurriculumModule | null): ModuleDraft {
  if (!module) {
    return EMPTY_MODULE;
  }
  return {
    id: module.id,
    name: module.name,
    description: module.description ?? '',
    order_index: String(module.order_index ?? 0),
  };
}

function buildTopicDraft(topic: CurriculumTopic | null): TopicDraft {
  if (!topic) {
    return EMPTY_TOPIC;
  }
  return {
    id: topic.id,
    name: topic.name,
    description: topic.description ?? '',
    order_index: String(topic.order_index ?? 0),
  };
}

export default function AdminCurriculumPage() {
  const queryClient = useQueryClient();

  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [selectedModuleId, setSelectedModuleId] = useState<string>('');
  const [selectedTopicId, setSelectedTopicId] = useState<string>('');
  const [subjectDraft, setSubjectDraft] = useState<SubjectDraft>(EMPTY_SUBJECT);
  const [moduleDraft, setModuleDraft] = useState<ModuleDraft>(EMPTY_MODULE);
  const [topicDraft, setTopicDraft] = useState<TopicDraft>(EMPTY_TOPIC);
  const [groupAssignments, setGroupAssignments] = useState<Record<string, string>>({});
  const [questionAssignments, setQuestionAssignments] = useState<Record<string, string>>({});

  const { data: treeData, isLoading: treeLoading } = useQuery({
    queryKey: ['admin-curriculum-tree'],
    queryFn: async () => {
      const response = await api.get('/admin/curriculum/tree');
      return (response.data.data ?? response.data) as CurriculumTree;
    },
  });

  const { data: reviewQueue, isLoading: queueLoading } = useQuery({
    queryKey: ['admin-curriculum-review-queue'],
    queryFn: async () => {
      const response = await api.get('/admin/curriculum/review-queue');
      return (response.data.data ?? response.data) as CurriculumReviewQueue;
    },
  });

  const subjects: CurriculumSubject[] = treeData?.subjects ?? [];
  const activeSubject = subjects.find((subject) => subject.id === selectedSubjectId) ?? subjects[0] ?? null;
  const activeSubjectId = activeSubject?.id ?? '';
  const modules: CurriculumModule[] = activeSubject?.modules ?? [];
  const activeModule = modules.find((module) => module.id === selectedModuleId) ?? modules[0] ?? null;
  const activeModuleId = activeModule?.id ?? '';
  const topics: CurriculumTopic[] = activeModule?.topics ?? [];
  const activeTopic = topics.find((topic) => topic.id === selectedTopicId) ?? topics[0] ?? null;
  const activeTopicId = activeTopic?.id ?? '';
  const currentSubjectDraft =
    subjectDraft.id || subjectDraft.name || subjectDraft.code || subjectDraft.description
      ? subjectDraft
      : buildSubjectDraft(activeSubject);
  const currentModuleDraft =
    moduleDraft.id || moduleDraft.name || moduleDraft.description || moduleDraft.order_index !== '0'
      ? moduleDraft
      : buildModuleDraft(activeModule);
  const currentTopicDraft =
    topicDraft.id || topicDraft.name || topicDraft.description || topicDraft.order_index !== '0'
      ? topicDraft
      : buildTopicDraft(activeTopic);
  const allTopics: CurriculumTopic[] = subjects.flatMap((subject) =>
    (subject.modules ?? []).flatMap((module) =>
      (module.topics ?? []).map((topic) => ({
        ...topic,
        module_name: topic.module_name ?? module.name,
        subject_id: topic.subject_id ?? subject.id,
        subject_name: topic.subject_name ?? subject.name,
      })),
    ),
  );

  const invalidateCurriculum = () => {
    queryClient.invalidateQueries({ queryKey: ['admin-curriculum-tree'] });
    queryClient.invalidateQueries({ queryKey: ['admin-curriculum-review-queue'] });
    queryClient.invalidateQueries({ queryKey: ['admin-groups'] });
  };

  const syncMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/admin/curriculum/sync-legacy');
      return response.data.data ?? response.data;
    },
    onSuccess: (result) => {
      toast.success(
        `Legacy sync complete: ${result.mapped_groups ?? 0} groups, ${result.mapped_questions ?? 0} questions mapped.`,
      );
      invalidateCurriculum();
    },
    onError: () => toast.error('Legacy sync failed'),
  });

  const subjectMutation = useMutation({
    mutationFn: async (payload: SubjectDraft) => {
      if (payload.id) {
        const response = await api.patch(`/admin/curriculum/subjects/${payload.id}`, {
          name: payload.name,
          code: payload.code || undefined,
          description: payload.description || undefined,
        });
        return response.data.data ?? response.data;
      }

      const response = await api.post('/admin/curriculum/subjects', {
        name: payload.name,
        code: payload.code || undefined,
        description: payload.description || undefined,
      });
      return response.data.data ?? response.data;
    },
    onSuccess: () => {
      toast.success('Subject saved');
      invalidateCurriculum();
    },
    onError: () => toast.error('Failed to save subject'),
  });

  const moduleMutation = useMutation({
    mutationFn: async (payload: ModuleDraft) => {
      if (!activeSubjectId) {
        throw new Error('Select a subject first');
      }

      if (payload.id) {
        const response = await api.patch(`/admin/curriculum/modules/${payload.id}`, {
          subject_id: activeSubjectId,
          name: payload.name,
          description: payload.description || undefined,
          order_index: Number(payload.order_index || 0),
        });
        return response.data.data ?? response.data;
      }

      const response = await api.post('/admin/curriculum/modules', {
        subject_id: activeSubjectId,
        name: payload.name,
        description: payload.description || undefined,
        order_index: Number(payload.order_index || 0),
      });
      return response.data.data ?? response.data;
    },
    onSuccess: () => {
      toast.success('Module saved');
      invalidateCurriculum();
    },
    onError: () => toast.error('Failed to save module'),
  });

  const topicMutation = useMutation({
    mutationFn: async (payload: TopicDraft) => {
      if (!activeModuleId) {
        throw new Error('Select a module first');
      }

      if (payload.id) {
        const response = await api.patch(`/admin/curriculum/topics/${payload.id}`, {
          module_id: activeModuleId,
          name: payload.name,
          description: payload.description || undefined,
          order_index: Number(payload.order_index || 0),
        });
        return response.data.data ?? response.data;
      }

      const response = await api.post('/admin/curriculum/topics', {
        module_id: activeModuleId,
        name: payload.name,
        description: payload.description || undefined,
        order_index: Number(payload.order_index || 0),
      });
      return response.data.data ?? response.data;
    },
    onSuccess: () => {
      toast.success('Topic saved');
      invalidateCurriculum();
    },
    onError: () => toast.error('Failed to save topic'),
  });

  const mapGroupMutation = useMutation({
    mutationFn: async ({ groupId, subjectId }: { groupId: string; subjectId: string }) => {
      await api.patch(`/admin/curriculum/groups/${groupId}/subject`, { subject_id: subjectId });
    },
    onSuccess: () => {
      toast.success('Group mapped');
      invalidateCurriculum();
    },
    onError: () => toast.error('Failed to map group'),
  });

  const mapQuestionMutation = useMutation({
    mutationFn: async ({ questionId, topicId }: { questionId: string; topicId: string }) => {
      await api.patch(`/admin/curriculum/questions/${questionId}/topic`, { topic_id: topicId });
    },
    onSuccess: () => {
      toast.success('Question mapped');
      invalidateCurriculum();
    },
    onError: () => toast.error('Failed to map question'),
  });

  const handleSelectSubject = (subjectId: string) => {
    const subject = subjects.find((item) => item.id === subjectId) ?? null;
    const firstModule = subject?.modules?.[0] ?? null;
    const firstTopic = firstModule?.topics?.[0] ?? null;

    setSelectedSubjectId(subjectId);
    setSubjectDraft(buildSubjectDraft(subject));
    setSelectedModuleId(firstModule?.id ?? '');
    setModuleDraft(buildModuleDraft(firstModule));
    setSelectedTopicId(firstTopic?.id ?? '');
    setTopicDraft(buildTopicDraft(firstTopic));
  };

  const handleSelectModule = (moduleId: string) => {
    const module = modules.find((item) => item.id === moduleId) ?? null;
    const firstTopic = module?.topics?.[0] ?? null;

    setSelectedModuleId(moduleId);
    setModuleDraft(buildModuleDraft(module));
    setSelectedTopicId(firstTopic?.id ?? '');
    setTopicDraft(buildTopicDraft(firstTopic));
  };

  const handleSelectTopic = (topicId: string) => {
    const topic = topics.find((item) => item.id === topicId) ?? null;
    setSelectedTopicId(topicId);
    setTopicDraft(buildTopicDraft(topic));
  };

  const handleSubjectSave = () => {
    if (!currentSubjectDraft.name.trim()) {
      toast.error('Subject name is required');
      return;
    }
    subjectMutation.mutate(currentSubjectDraft);
  };

  const handleModuleSave = () => {
    if (!activeSubjectId) {
      toast.error('Select a subject first');
      return;
    }
    if (!currentModuleDraft.name.trim()) {
      toast.error('Module name is required');
      return;
    }
    moduleMutation.mutate(currentModuleDraft);
  };

  const handleTopicSave = () => {
    if (!activeModuleId) {
      toast.error('Select a module first');
      return;
    }
    if (!currentTopicDraft.name.trim()) {
      toast.error('Topic name is required');
      return;
    }
    topicMutation.mutate(currentTopicDraft);
  };

  if (treeLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Curriculum</h1>
          <p className={styles.subtitle}>
            Structure assessments under subject, module, and topic while reviewing legacy mappings.
          </p>
        </div>
        <Button icon={<FiRefreshCw />} loading={syncMutation.isPending} onClick={() => syncMutation.mutate()}>
          Sync Legacy Data
        </Button>
      </div>

      {!subjects.length ? (
        <EmptyState
          icon={<FiBookOpen size={40} />}
          title="No curriculum yet"
          description="Create a subject to start building the academic structure."
        />
      ) : null}

      <div className={styles.grid}>
        <Card title="Subjects" actions={<Badge variant="info">{subjects.length}</Badge>}>
          <div className={styles.cardContent}>
            <div className={styles.list}>
              {subjects.map((subject) => (
                <button
                  key={subject.id}
                  type="button"
                  className={`${styles.listItem} ${subject.id === activeSubjectId ? styles.active : ''}`}
                  onClick={() => handleSelectSubject(subject.id)}
                >
                  <div>
                    <strong>{subject.name}</strong>
                    <span>{subject.modules?.length ?? 0} modules</span>
                  </div>
                  <FiArrowRight />
                </button>
              ))}
            </div>

            <div className={styles.editor}>
              <div className={styles.editorHeader}>
                <h3>{currentSubjectDraft.id ? 'Edit Subject' : 'New Subject'}</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSelectedSubjectId('');
                    setSubjectDraft(EMPTY_SUBJECT);
                  }}
                >
                  New
                </Button>
              </div>
              <Input
                label="Name"
                value={currentSubjectDraft.name}
                onChange={(event) => setSubjectDraft((prev) => ({ ...prev, name: event.target.value }))}
              />
              <Input
                label="Code"
                value={currentSubjectDraft.code}
                onChange={(event) => setSubjectDraft((prev) => ({ ...prev, code: event.target.value }))}
              />
              <Textarea
                label="Description"
                rows={4}
                value={currentSubjectDraft.description}
                onChange={(event) => setSubjectDraft((prev) => ({ ...prev, description: event.target.value }))}
              />
              <Button icon={<FiSave />} loading={subjectMutation.isPending} onClick={handleSubjectSave}>
                Save Subject
              </Button>
            </div>
          </div>
        </Card>

        <Card title="Modules" actions={<Badge variant="warning">{modules.length}</Badge>}>
          <div className={styles.cardContent}>
            <div className={styles.list}>
              {(modules.length ? modules : []).map((module) => (
                <button
                  key={module.id}
                  type="button"
                  className={`${styles.listItem} ${module.id === activeModuleId ? styles.active : ''}`}
                  onClick={() => handleSelectModule(module.id)}
                >
                  <div>
                    <strong>{module.name}</strong>
                    <span>{module.topics?.length ?? 0} topics</span>
                  </div>
                  <FiArrowRight />
                </button>
              ))}
              {!modules.length && <p className={styles.emptyText}>Select or create a subject to add modules.</p>}
            </div>

            <div className={styles.editor}>
              <div className={styles.editorHeader}>
                <h3>{currentModuleDraft.id ? 'Edit Module' : 'New Module'}</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSelectedModuleId('');
                    setModuleDraft(EMPTY_MODULE);
                  }}
                >
                  New
                </Button>
              </div>
              <Input
                label="Name"
                value={currentModuleDraft.name}
                onChange={(event) => setModuleDraft((prev) => ({ ...prev, name: event.target.value }))}
              />
              <Input
                label="Order"
                type="number"
                value={currentModuleDraft.order_index}
                onChange={(event) => setModuleDraft((prev) => ({ ...prev, order_index: event.target.value }))}
              />
              <Textarea
                label="Description"
                rows={4}
                value={currentModuleDraft.description}
                onChange={(event) => setModuleDraft((prev) => ({ ...prev, description: event.target.value }))}
              />
              <Button icon={<FiSave />} loading={moduleMutation.isPending} onClick={handleModuleSave}>
                Save Module
              </Button>
            </div>
          </div>
        </Card>

        <Card title="Topics" actions={<Badge variant="success">{topics.length}</Badge>}>
          <div className={styles.cardContent}>
            <div className={styles.list}>
              {(topics.length ? topics : []).map((topic) => (
                <button
                  key={topic.id}
                  type="button"
                  className={`${styles.listItem} ${topic.id === activeTopicId ? styles.active : ''}`}
                  onClick={() => handleSelectTopic(topic.id)}
                >
                  <div>
                    <strong>{topic.name}</strong>
                    <span>{topic.subject_name ?? activeSubject?.name ?? 'Unassigned subject'}</span>
                  </div>
                  <FiArrowRight />
                </button>
              ))}
              {!topics.length && <p className={styles.emptyText}>Select or create a module to add topics.</p>}
            </div>

            <div className={styles.editor}>
              <div className={styles.editorHeader}>
                <h3>{currentTopicDraft.id ? 'Edit Topic' : 'New Topic'}</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSelectedTopicId('');
                    setTopicDraft(EMPTY_TOPIC);
                  }}
                >
                  New
                </Button>
              </div>
              <Input
                label="Name"
                value={currentTopicDraft.name}
                onChange={(event) => setTopicDraft((prev) => ({ ...prev, name: event.target.value }))}
              />
              <Input
                label="Order"
                type="number"
                value={currentTopicDraft.order_index}
                onChange={(event) => setTopicDraft((prev) => ({ ...prev, order_index: event.target.value }))}
              />
              <Textarea
                label="Description"
                rows={4}
                value={currentTopicDraft.description}
                onChange={(event) => setTopicDraft((prev) => ({ ...prev, description: event.target.value }))}
              />
              <Button icon={<FiSave />} loading={topicMutation.isPending} onClick={handleTopicSave}>
                Save Topic
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <div className={styles.reviewGrid}>
        <Card
          title="Unmapped Groups"
          actions={<Badge variant="neutral">{reviewQueue?.groups.length ?? 0}</Badge>}
        >
          {queueLoading ? (
            <div className={styles.center}>
              <Spinner />
            </div>
          ) : !(reviewQueue?.groups.length ?? 0) ? (
            <p className={styles.emptyText}>All groups are linked to a curriculum subject.</p>
          ) : (
            <div className={styles.reviewList}>
              {reviewQueue?.groups.map((item) => (
                <div key={item.group_id} className={styles.reviewItem}>
                  <div className={styles.reviewMeta}>
                    <strong>{item.group_name}</strong>
                    <span>Legacy subject: {item.legacy_subject || 'Not provided'}</span>
                    {item.suggested_subject_name && (
                      <Badge variant="info">Suggested: {item.suggested_subject_name}</Badge>
                    )}
                  </div>
                  <div className={styles.reviewActions}>
                    <select
                      className={styles.inlineSelect}
                      value={groupAssignments[item.group_id] ?? item.suggested_subject_id ?? ''}
                      onChange={(event) =>
                        setGroupAssignments((prev) => ({ ...prev, [item.group_id]: event.target.value }))
                      }
                    >
                      <option value="">Select subject</option>
                      {subjects.map((subject) => (
                        <option key={subject.id} value={subject.id}>
                          {subject.name}
                        </option>
                      ))}
                    </select>
                    <Button
                      size="sm"
                      onClick={() =>
                        mapGroupMutation.mutate({
                          groupId: item.group_id,
                          subjectId: groupAssignments[item.group_id] ?? item.suggested_subject_id ?? '',
                        })
                      }
                      disabled={!(groupAssignments[item.group_id] ?? item.suggested_subject_id)}
                      loading={mapGroupMutation.isPending}
                    >
                      Map
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card
          title="Unmapped Questions"
          actions={<Badge variant="neutral">{reviewQueue?.questions.length ?? 0}</Badge>}
        >
          {queueLoading ? (
            <div className={styles.center}>
              <Spinner />
            </div>
          ) : !(reviewQueue?.questions.length ?? 0) ? (
            <p className={styles.emptyText}>All questions with topic tags are linked to a curriculum topic.</p>
          ) : (
            <div className={styles.reviewList}>
              {reviewQueue?.questions.map((item) => {
                const topicOptions = allTopics.filter((topic) =>
                  item.subject_id ? topic.subject_id === item.subject_id : true,
                );

                return (
                  <div key={item.question_id} className={styles.reviewItem}>
                    <div className={styles.reviewMeta}>
                      <strong>{item.assessment_title || 'Question bank item'}</strong>
                      <span>{item.content_preview}</span>
                      <span>Legacy topic: {item.legacy_topic || 'Not provided'}</span>
                      <div className={styles.badgeRow}>
                        {item.subject_name && <Badge variant="warning">{item.subject_name}</Badge>}
                        {item.suggested_topic_name && <Badge variant="info">Suggested: {item.suggested_topic_name}</Badge>}
                      </div>
                    </div>
                    <div className={styles.reviewActions}>
                      <select
                        className={styles.inlineSelect}
                        value={questionAssignments[item.question_id] ?? item.suggested_topic_id ?? ''}
                        onChange={(event) =>
                          setQuestionAssignments((prev) => ({ ...prev, [item.question_id]: event.target.value }))
                        }
                      >
                        <option value="">Select topic</option>
                        {topicOptions.map((topic) => (
                          <option key={topic.id} value={topic.id}>
                            {topic.subject_name} / {topic.module_name} / {topic.name}
                          </option>
                        ))}
                      </select>
                      <Button
                        size="sm"
                        onClick={() =>
                          mapQuestionMutation.mutate({
                            questionId: item.question_id,
                            topicId: questionAssignments[item.question_id] ?? item.suggested_topic_id ?? '',
                          })
                        }
                        disabled={!(questionAssignments[item.question_id] ?? item.suggested_topic_id)}
                        loading={mapQuestionMutation.isPending}
                      >
                        Map
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
