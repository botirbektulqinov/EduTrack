import { useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { FiPlay } from 'react-icons/fi';
import type { CodeQuestionConfig, CodeQuestionTestCase, CodeRunResult, Question } from '@/types';
import Button from '@/components/ui/Button';
import s from './CodeQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
  onRunCodePreview?: (questionId: string, codeSubmission: string) => Promise<CodeRunResult>;
  runResult?: CodeRunResult | null;
  isRunning?: boolean;
}

function buildPlaceholder(config: CodeQuestionConfig) {
  if (config.execution_mode === 'function') {
    const functionName = config.function_name || 'solve';
    return `def ${functionName}(input_data: str):\n    # return the final answer\n    pass`;
  }

  return '# Read from stdin and print the result';
}

function editorLanguage(language?: string) {
  switch ((language ?? 'python').toLowerCase()) {
    case 'javascript':
      return 'javascript';
    case 'java':
      return 'java';
    case 'cpp':
      return 'cpp';
    default:
      return 'python';
  }
}

export function CodeQuestion({
  question,
  value,
  onChange,
  onRunCodePreview,
  runResult,
  isRunning = false,
}: Props) {
  const config = (question.config ?? {}) as CodeQuestionConfig;
  const code = typeof value === 'string' ? value : '';
  const starterCode = config.starter_code ?? '';
  const visibleTestCases: CodeQuestionTestCase[] =
    config.visible_test_cases ??
    config.test_cases?.filter((testCase) => !testCase.is_hidden) ??
    [];

  useEffect(() => {
    if (!code && starterCode) {
      onChange(starterCode);
    }
  }, [code, starterCode, onChange]);

  const handleRun = async () => {
    if (!onRunCodePreview || !code.trim()) {
      return;
    }
    await onRunCodePreview(question.id, code);
  };

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />

      <div className={s.meta}>
        <span className={s.metaChip}>Language: {(config.language ?? 'python').toUpperCase()}</span>
        <span className={s.metaChip}>
          Mode: {config.execution_mode === 'function' ? 'Function' : 'Standard IO'}
        </span>
        {config.execution_mode === 'function' && config.function_name && (
          <span className={s.metaChip}>Function: {config.function_name}</span>
        )}
        {config.time_limit_seconds && (
          <span className={s.metaChip}>Time Limit: {config.time_limit_seconds}s</span>
        )}
      </div>

      {config.execution_mode === 'function' ? (
        <p className={s.helper}>
          Implement <code>{config.function_name || 'solve'}</code> and return the final answer.
          The raw test input will be passed as a single string argument.
        </p>
      ) : (
        <p className={s.helper}>
          Read input from standard input and print the final answer exactly as expected.
        </p>
      )}

      {visibleTestCases.length > 0 && (
        <div className={s.cases}>
          <div className={s.casesHeader}>
            <h4 className={s.casesTitle}>Visible Test Cases</h4>
            {onRunCodePreview && (
              <Button
                size="sm"
                icon={<FiPlay />}
                onClick={handleRun}
                loading={isRunning}
                disabled={!code.trim()}
              >
                Run Visible Tests
              </Button>
            )}
          </div>
          <div className={s.caseGrid}>
            {visibleTestCases.map((testCase, index) => (
              <div key={`${index}-${testCase.input}-${testCase.output}`} className={s.caseCard}>
                <div className={s.caseLabel}>Case {index + 1}</div>
                <div className={s.caseBlock}>
                  <span>Input</span>
                  <pre>{testCase.input || '<empty>'}</pre>
                </div>
                <div className={s.caseBlock}>
                  <span>Expected Output</span>
                  <pre>{testCase.output || '<empty>'}</pre>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={s.editorWrap}>
        <Editor
          height="360px"
          language={editorLanguage(config.language)}
          theme="vs-dark"
          value={code}
          onChange={(nextValue) => onChange(nextValue ?? '')}
          options={{
            automaticLayout: true,
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            tabSize: 2,
            insertSpaces: true,
            quickSuggestions: false,
            lineNumbersMinChars: 3,
          }}
          loading={<div className={s.editorLoading}>Loading editor...</div>}
          defaultValue={starterCode || buildPlaceholder(config)}
        />
      </div>

      {runResult && (
        <div className={s.runResults}>
          <div className={s.runSummary}>
            <strong>
              Visible tests: {runResult.passed_cases}/{runResult.total_cases} passed
            </strong>
            <span>{runResult.feedback}</span>
          </div>
          <div className={s.runCaseList}>
            {runResult.cases.map((runCase) => (
              <div
                key={`${runCase.index}-${runCase.input}-${runCase.expected_output}`}
                className={`${s.runCaseCard} ${runCase.passed ? s.pass : s.fail}`}
              >
                <div className={s.runCaseHeader}>
                  <span>Case {runCase.index}</span>
                  <span>{runCase.passed ? 'Passed' : 'Failed'}</span>
                </div>
                <div className={s.caseBlock}>
                  <span>Input</span>
                  <pre>{runCase.input || '<empty>'}</pre>
                </div>
                <div className={s.caseBlock}>
                  <span>Expected Output</span>
                  <pre>{runCase.expected_output || '<empty>'}</pre>
                </div>
                <div className={s.caseBlock}>
                  <span>Actual Output</span>
                  <pre>{runCase.actual_output || '<empty>'}</pre>
                </div>
                {runCase.error && (
                  <div className={s.caseBlock}>
                    <span>Error</span>
                    <pre>{runCase.error}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
