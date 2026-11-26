### Feature

1. Trace the affected code. State the triggering input and the observable result.
2. For a change across interfaces, use the [design workflow selection criteria](../../fstack/references/workflows.md#design-requests). Identify the owner of shared state before splitting work.
3. Implement the smallest complete change. Work locally for a single coherent task. Delegate when the request and host authorize it and the work benefits from an independent owner. Give each worker a bounded scope and a verification criterion.
4. Verify the behavior through the relevant entry point. Report what ran, what passed and any unverified surface.
5. Finish with the verified local diff for an implementation request. When commits are authorized, group verified changes into coherent commits. When publication is authorized, follow [Opening a PR](opening-a-pr.md).
