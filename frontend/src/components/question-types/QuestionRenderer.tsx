import type { CodeRunResult, Question } from '@/types';
import { TrueFalseQuestion } from './TrueFalseQuestion';
import { MCQSingleQuestion } from './MCQSingleQuestion';
import { MCQMultiQuestion } from './MCQMultiQuestion';
import { ShortAnswerQuestion } from './ShortAnswerQuestion';
import { EssayQuestion } from './EssayQuestion';
import { FillBlankQuestion } from './FillBlankQuestion';
import { NumericQuestion } from './NumericQuestion';
import { MatchingQuestion } from './MatchingQuestion';
import { OrderingQuestion } from './OrderingQuestion';
import { LikertQuestion } from './LikertQuestion';
import { CodeQuestion } from './CodeQuestion';
import { ImageMCQQuestion } from './ImageMCQQuestion';
import { CategorizeQuestion } from './CategorizeQuestion';
import { HotspotQuestion } from './HotspotQuestion';

export interface QuestionRendererProps {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
  onRunCodePreview?: (questionId: string, codeSubmission: string) => Promise<CodeRunResult>;
  codeRunResult?: CodeRunResult | null;
  isRunningCode?: boolean;
}

export function QuestionRenderer({
  question,
  value,
  onChange,
  onRunCodePreview,
  codeRunResult,
  isRunningCode,
}: QuestionRendererProps) {
  switch (question.question_type) {
    case 'true_false':
    case 'yes_no':
      return <TrueFalseQuestion question={question} value={value} onChange={onChange} />;
    case 'mcq_single':
      return <MCQSingleQuestion question={question} value={value} onChange={onChange} />;
    case 'mcq_multi':
      return <MCQMultiQuestion question={question} value={value} onChange={onChange} />;
    case 'image_mcq':
      return <ImageMCQQuestion question={question} value={value} onChange={onChange} />;
    case 'short_answer':
      return <ShortAnswerQuestion question={question} value={value} onChange={onChange} />;
    case 'essay':
      return <EssayQuestion question={question} value={value} onChange={onChange} />;
    case 'fill_blank':
      return <FillBlankQuestion question={question} value={value} onChange={onChange} />;
    case 'numeric':
      return <NumericQuestion question={question} value={value} onChange={onChange} />;
    case 'matching':
      return <MatchingQuestion question={question} value={value} onChange={onChange} />;
    case 'ordering':
      return <OrderingQuestion question={question} value={value} onChange={onChange} />;
    case 'categorization':
      return <CategorizeQuestion question={question} value={value} onChange={onChange} />;
    case 'hotspot':
      return <HotspotQuestion question={question} value={value} onChange={onChange} />;
    case 'code':
      return (
        <CodeQuestion
          question={question}
          value={value}
          onChange={onChange}
          onRunCodePreview={onRunCodePreview}
          runResult={codeRunResult}
          isRunning={isRunningCode}
        />
      );
    case 'likert':
      return <LikertQuestion question={question} value={value} onChange={onChange} />;
    case 'audio_video':
      return <div>Audio/Video questions are not yet supported.</div>;
    default:
      return <div>Unsupported question type: {question.question_type}</div>;
  }
}
