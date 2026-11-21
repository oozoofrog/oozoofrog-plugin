# App Store rating and review requests

Use this reference for iPhone, iPad, Mac Catalyst and native Mac apps. Check the declarations in the project's selected Xcode SDK and the app's deployment target before editing. An older compiler may lack a symbol supported by the deployment OS.

| Integration | Availability | Call and presentation context |
| --- | --- | --- |
| SwiftUI | iOS, iPadOS and Catalyst 16+, macOS 13+ | Import SwiftUI and StoreKit. Read `@Environment(\.requestReview) private var requestReview` in the originating view. Call `requestReview()` on the main actor. |
| UIKit | iOS, iPadOS and Catalyst 16+ | Call `AppStore.requestReview(in: scene)` on the main actor. Get the active `UIWindowScene` from the window containing the completed workflow. |
| AppKit | macOS 13+ | Call `AppStore.requestReview(in: controller)` on the main actor with the visible window's attached `NSViewController`. |
| Legacy scene API | iOS/iPadOS 14+, Catalyst 14+ | For older deployment targets, pass the originating scene to `SKStoreReviewController.requestReview(in:)`. Deprecated with iOS 18. |
| Legacy process-wide API | iOS 10.3+, Catalyst 13.1+, macOS 10.14+ | Where the newer call is unavailable, use `SKStoreReviewController.requestReview()`. Deprecated with iOS 14 and macOS 15. |
| User-initiated link | App Store product page | Open `https://apps.apple.com/app/id<NUMERIC_ID>?action=write-review` from an explicit Settings or Help action. Preserve any existing URL parameters when adding the query item. |

The SwiftUI environment value supplies a `RequestReviewAction`. Calling it invokes `callAsFunction()`. All automatic APIs return Void. Apple exposes no supported query for remaining quota, past individual feedback, opt-out, or whether a request produced UI. Skip automatic requests on systems below the supported API range. [SwiftUI](https://developer.apple.com/documentation/storekit/requestreviewaction) · [UIKit](https://developer.apple.com/documentation/storekit/appstore/requestreview%28in%3A%29-1q8qs) · [AppKit](https://developer.apple.com/documentation/storekit/appstore/requestreview%28in%3A%29-4r0y9) · [Legacy controller](https://developer.apple.com/documentation/storekit/skstorereviewcontroller)

## Presentation and testing

- In production, for someone who has not rated or reviewed the app on that device, StoreKit allows at most three presentations in 365 days. After a rating or review, eligibility requires a new app version and more than 365 days since the previous review. A user can disable system requests. Let StoreKit apply these rules.
- In development mode, Apple documents that the request displays for UI testing. In TestFlight the request has no effect. A deterministic test should observe the app's decision and invocation. Neither the test nor the development dialog predicts production display.
- Decide when to request independently of the system limit. Apple suggests allowing at least a week or two and waiting for further engagement. Apple's sample uses completed tasks and the app version. Its example count and delay are product choices. [StoreKit behavior](https://developer.apple.com/documentation/storekit/requestreviewaction) · [Apple sample](https://developer.apple.com/documentation/storekit/requesting-app-store-reviews) · [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/ratings-and-reviews)

## Store policy and measurement

Use the system prompt for automatic requests. A persistent product-page link lets people initiate a review at any time. Offer support independently of the rating flow. Apple prohibits custom review prompts and manipulation of reviews. [App Review Guidelines §§5.6.1 and 5.6.3](https://developer.apple.com/app-store/review/guidelines/#app-store-reviews)

Ratings appear in search and on the product page. Summary ratings are storefront-specific. App Store Connect lets the developer inspect published feedback and respond. Its customer review API serves that administrative purpose and cannot trigger a prompt or identify which in-app attempt caused a review. No credentials or App Store Connect integration are needed to add a prompt. [Ratings and reviews](https://developer.apple.com/app-store/ratings-and-reviews/) · [App Store Connect customer reviews](https://developer.apple.com/documentation/appstoreconnectapi/customer-reviews)
