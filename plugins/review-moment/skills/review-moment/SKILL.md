---
name: review-moment
description: Choose an app-specific moment to request App Store ratings and reviews and implement it in an iOS or macOS app using StoreKit. 앱의 핵심 작업을 분석해 별점·리뷰 요청 시점을 고르고 구현할 때 사용한다.
---

# Review Moment

Read the [StoreKit API guide](references/storekit.md) when choosing a call, checking supported OS versions, or testing presentation.

## Choose the moment from the app

Trace the user's main job through the actual app. Locate the event that confirms its outcome and the UI the person sees next. Inspect existing review calls, version gates, distribution channels, supported OS versions, and available engagement data. Preserve intentional product rules. For a Mac app with multiple editions, enable the integration only in the App Store edition unless the product explicitly links another edition to its store listing.

Compare plausible moments by the value the user has already experienced, how many experienced users reach the moment, and what a prompt would interrupt. Name the event and the code that proves it occurred. Use actual counts if available. Label reach or impact estimates as hypotheses. Choose the strongest supported opportunity and explain the tradeoff against the next candidate. If the flow offers no quiet moment yet, identify the next observable pause before inserting a request.

For example, an editor can observe a finished export after the destination sheet closes. A game can use the results screen after a completed round, regardless of the score. A utility used only once may deliver its full value on the first completed job. A daily tracker may need several completed sessions before a person can judge it. Derive thresholds from the product's cadence. Treat first launch, onboarding, purchase authorization, active input and error recovery as poor interruption points.

## Implement the selected opportunity

1. State the triggering event, engagement condition, foreground UI state, and expected number of API attempts. Modify the actual completion and presentation paths. Reuse the app's state and persistence.
2. Apply the same opportunity to people who complete the same workflow. Never select people by satisfaction, spending, predicted stars or survey answers. Do not use rewards, a custom rating prompt, or a “like the app?” filter.
3. Tie pending work to the originating view or scene. If the user starts another task, leaves, backgrounds the app, or another sheet opens, cancel or recheck before calling StoreKit. A fixed delay alone cannot establish readiness.
4. Serialize the final eligibility check and record the attempt with the StoreKit call. Use shared app state across windows. Make duplicate events and relaunches safe. Select a local cooldown and/or marketing-version rule suited to release cadence. A new release alone does not establish renewed engagement.
5. Keep explicit “Write a review” controls on the product-page link path. Reuse the verified store ID for the correct listing. The automatic call needs no store ID.

## Verify and report

Run the app's normal workflow with a fresh state and with prior state. Verify the eligible path reaches the request once. Exercise early use, interrupted work, duplicate delivery and relaunch as applicable. Use an injected recorder for deterministic counts and build the real StoreKit path for each affected platform. If a development UI run is available, record separately what was visible. Report changed files, commands, the chosen moment, and unverified configurations.

If business measurement is in scope, use existing analytics to compare aggregate rating volume per active device and task completion or abandonment across comparable periods and storefronts. Record eligible events and request attempts only where the app can observe them. StoreKit returns no individual rating, submission, or presentation receipt. Changes in release quality, reach and audience can affect the same metrics. Avoid promising an uplift.
