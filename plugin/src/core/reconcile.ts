export const STATUS_PREFIX = 'status/';
export const PRIORITY_PREFIX = 'priority/';

export interface Reconciliation {
  tags: Set<string>;
  autoTags: Set<string>;
  suppressedTags: Set<string>;
}

export interface ReconcileOptions {
  suppressedTags?: Set<string>;
  allowTagRemoval?: boolean;
}

/**
 * Reconcile current Zotero tags with accepted classification decisions.
 * Preserves human tags, suppresses deleted auto tags, and rejects status/priority mutations.
 */
export function reconcile(
  current: Set<string>,
  previousAuto: Set<string>,
  accepted: Set<string>,
  options: ReconcileOptions = {}
): Reconciliation {
  const { suppressedTags = new Set<string>(), allowTagRemoval = true } = options;

  // Workflow status & priority are exclusively human-owned
  const cleanPrevAuto = new Set(
    [...previousAuto].filter(
      (t) => !t.startsWith(STATUS_PREFIX) && !t.startsWith(PRIORITY_PREFIX)
    )
  );
  const cleanAccepted = new Set(
    [...accepted].filter(
      (t) => !t.startsWith(STATUS_PREFIX) && !t.startsWith(PRIORITY_PREFIX)
    )
  );
  const cleanSuppressed = new Set(
    [...suppressedTags].filter(
      (t) => !t.startsWith(STATUS_PREFIX) && !t.startsWith(PRIORITY_PREFIX)
    )
  );

  // Absence of a formerly-owned auto tag is a durable human suppression
  const deletedAuto = new Set([...cleanPrevAuto].filter((t) => !current.has(t)));
  const suppressed = new Set([...cleanSuppressed, ...deletedAuto]);

  const retainedAuto = new Set([...cleanPrevAuto].filter((t) => current.has(t)));
  // Tags that already exist but are not ours remain human-owned
  const newAuto = new Set([...cleanAccepted].filter((t) => !current.has(t)));

  const desiredAuto = new Set<string>();
  for (const tag of retainedAuto) {
    if (cleanAccepted.has(tag) && !suppressed.has(tag)) {
      desiredAuto.add(tag);
    }
  }
  for (const tag of newAuto) {
    if (!suppressed.has(tag)) {
      desiredAuto.add(tag);
    }
  }

  if (!allowTagRemoval) {
    for (const tag of retainedAuto) {
      desiredAuto.add(tag);
    }
  }

  // Final tags = (current - retainedAuto) | desiredAuto
  const humanTags = new Set([...current].filter((t) => !retainedAuto.has(t)));
  const finalTags = new Set([...humanTags, ...desiredAuto]);

  return {
    tags: finalTags,
    autoTags: desiredAuto,
    suppressedTags: suppressed,
  };
}
