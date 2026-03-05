/* ─── EduTrack — Proctoring SDK (§6, §11.2) ─── */
import type { ViolationType, ViolationEvent, ProctoringConfig } from '@/types';

const BLOCKED_SHORTCUTS: Array<{
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  meta?: boolean;
  reason: ViolationType;
}> = [
  { key: 'F12', reason: 'DEVTOOLS_DETECTED' },
  { key: 'F11', reason: 'F11_PRESSED' },
  { key: 'i', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'I', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'j', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'J', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'c', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'C', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'u', ctrl: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'U', ctrl: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 's', ctrl: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'S', ctrl: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'p', ctrl: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'P', ctrl: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'p', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'P', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'k', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'K', ctrl: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  // macOS variants
  { key: 'i', meta: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'j', meta: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'c', meta: true, shift: true, reason: 'DEVTOOLS_DETECTED' },
  { key: 'p', meta: true, reason: 'DEVTOOLS_DETECTED' },
];

export class ProctoringSDK {
  private violationCount = 0;
  private onViolation: (event: ViolationEvent) => void;
  private onTerminate: () => void;
  private maxViolations: number;
  private config: ProctoringConfig;
  private cleanupFns: Array<() => void> = [];
  private mutationObserver: MutationObserver | null = null;
  private devToolsInterval: ReturnType<typeof setInterval> | null = null;
  private active = false;

  constructor(config: ProctoringConfig, callbacks: {
    onViolation: (event: ViolationEvent) => void;
    onTerminate: () => void;
  }) {
    this.config = config;
    this.maxViolations = config.maxViolations;
    this.onViolation = callbacks.onViolation;
    this.onTerminate = callbacks.onTerminate;
  }

  init(): void {
    if (this.active) return;
    this.active = true;

    if (this.config.enforceFullscreen) {
      this.attachFullscreenListener();
    }
    if (this.config.blockKeyboardShortcuts) {
      this.attachKeydownBlocker();
    }
    if (this.config.tabSwitchDetection) {
      this.attachVisibilityListener();
    }
    this.attachBlurListener();
    if (this.config.rightClickBlock) {
      this.attachContextMenuBlocker();
    }
    this.attachBeforeUnloadGuard();
    if (this.config.devToolsDetection) {
      this.attachDevToolsDetector();
    }
    if (this.config.copyPasteBlock) {
      this.attachCopyPasteBlocker();
    }
    this.attachMutationObserver();
  }

  async enterFullscreen(): Promise<boolean> {
    try {
      await document.documentElement.requestFullscreen();
      return true;
    } catch {
      return false;
    }
  }

  private triggerViolation(type: ViolationType): void {
    if (!this.active) return;
    this.violationCount++;
    const event: ViolationEvent = {
      type,
      count: this.violationCount,
      timestamp: new Date().toISOString(),
    };
    this.onViolation(event);
    if (this.violationCount >= this.maxViolations) {
      this.onTerminate();
    }
  }

  /* ── Fullscreen ── */
  private attachFullscreenListener(): void {
    const handler = () => {
      if (!document.fullscreenElement) {
        this.triggerViolation('FULLSCREEN_EXIT');
      }
    };
    document.addEventListener('fullscreenchange', handler);
    document.addEventListener('webkitfullscreenchange', handler);
    this.cleanupFns.push(() => {
      document.removeEventListener('fullscreenchange', handler);
      document.removeEventListener('webkitfullscreenchange', handler);
    });
  }

  /* ── Keyboard shortcuts ── */
  private attachKeydownBlocker(): void {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        return;
      }

      for (const shortcut of BLOCKED_SHORTCUTS) {
        const ctrlMatch = shortcut.ctrl ? (e.ctrlKey || e.metaKey) : true;
        const shiftMatch = shortcut.shift ? e.shiftKey : !e.shiftKey || shortcut.ctrl;
        const metaMatch = shortcut.meta ? e.metaKey : true;

        if (e.key === shortcut.key && ctrlMatch && shiftMatch && metaMatch) {
          e.preventDefault();
          e.stopPropagation();
          this.triggerViolation(shortcut.reason);
          return;
        }
      }
    };
    document.addEventListener('keydown', handler, true);
    this.cleanupFns.push(() => document.removeEventListener('keydown', handler, true));
  }

  /* ── Tab visibility ── */
  private attachVisibilityListener(): void {
    const handler = () => {
      if (document.visibilityState === 'hidden') {
        this.triggerViolation('TAB_SWITCH');
      }
    };
    document.addEventListener('visibilitychange', handler);
    this.cleanupFns.push(() => document.removeEventListener('visibilitychange', handler));
  }

  /* ── Window blur ── */
  private attachBlurListener(): void {
    const handler = () => {
      this.triggerViolation('WINDOW_FOCUS_LOST');
    };
    window.addEventListener('blur', handler);
    this.cleanupFns.push(() => window.removeEventListener('blur', handler));
  }

  /* ── Context menu ── */
  private attachContextMenuBlocker(): void {
    const handler = (e: Event) => {
      e.preventDefault();
    };
    document.addEventListener('contextmenu', handler);
    this.cleanupFns.push(() => document.removeEventListener('contextmenu', handler));
  }

  /* ── Before unload ── */
  private attachBeforeUnloadGuard(): void {
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      this.triggerViolation('PAGE_UNLOAD_ATTEMPT');
      return (e.returnValue = '');
    };
    window.addEventListener('beforeunload', handler);
    this.cleanupFns.push(() => window.removeEventListener('beforeunload', handler));
  }

  /* ── DevTools detection (window size) ── */
  private attachDevToolsDetector(): void {
    this.devToolsInterval = setInterval(() => {
      const widthDiff = window.outerWidth - window.innerWidth;
      const heightDiff = window.outerHeight - window.innerHeight;
      if (widthDiff > 160 || heightDiff > 160) {
        this.triggerViolation('DEVTOOLS_DETECTED');
      }
    }, 3000);
    this.cleanupFns.push(() => {
      if (this.devToolsInterval) clearInterval(this.devToolsInterval);
    });
  }

  /* ── Copy / Paste block ── */
  private attachCopyPasteBlocker(): void {
    const blockHandler = (e: Event) => {
      const target = e.target as HTMLElement;
      // Allow in input/textarea fields
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;
      e.preventDefault();
    };
    document.addEventListener('copy', blockHandler, true);
    document.addEventListener('cut', blockHandler, true);
    document.addEventListener('paste', blockHandler, true);
    this.cleanupFns.push(() => {
      document.removeEventListener('copy', blockHandler, true);
      document.removeEventListener('cut', blockHandler, true);
      document.removeEventListener('paste', blockHandler, true);
    });
  }

  /* ── Mutation observer (injected scripts/iframes) ── */
  private attachMutationObserver(): void {
    this.mutationObserver = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of Array.from(mutation.addedNodes)) {
          if (node.nodeName === 'SCRIPT' || node.nodeName === 'IFRAME') {
            this.triggerViolation('INJECTED_ELEMENT_DETECTED');
          }
        }
      }
    });
    this.mutationObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
    this.cleanupFns.push(() => this.mutationObserver?.disconnect());
  }

  /* ── Cleanup ── */
  destroy(): void {
    this.active = false;
    this.cleanupFns.forEach((fn) => fn());
    this.cleanupFns = [];
  }

  getViolationCount(): number {
    return this.violationCount;
  }
}
