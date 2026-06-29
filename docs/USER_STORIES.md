# User Stories

## Authentication
- As a new user, I want to register with my email and password so I can access the platform.
- As a registered user, I want to log in with my credentials and receive a JWT so I can use the API.
- As a logged-in user, I want my session to expire after 24 hours so my account stays secure.

## Match Discovery
- As a user, I want to see a list of upcoming matches with dates and venues so I can plan my team selection.
- As a user, I want to know if the playing XI has been confirmed for a match so I can trust the predictions.
- As a user, I want to filter matches by format (T20, ODI, IPL) so I can focus on contests I play.

## Team Prediction
- As a free user, I want to generate 1 safe team for a match so I can get a quick recommendation.
- As a premium user, I want to generate up to 20 team combinations so I can diversify my entries.
- As a premium user, I want to generate a Grand League team with differential picks so I can win big.
- As a user, I want to see the total credits used by my generated team so I know it's within budget.
- As a user, I want to see the predicted fantasy points for each player so I can evaluate the selection.

## Captain Selection
- As a user, I want to see the top 3 captain options with confidence scores so I can make an informed choice.
- As a user, I want a "safe captain" and a "risk captain" recommendation so I can match my strategy.

## Explainability
- As a user, I want to understand why each player was selected so I can agree or disagree with the pick.
- As a user, I want to see a player's recent form data so I can verify the selection rationale.
- As a user, I want to know which human rules influenced a player's score so I can understand edge cases.

## AI Chat
- As a premium user, I want to ask "Who should I captain today?" in plain English so I get a direct answer.
- As a premium user, I want to ask "Why not Rohit Sharma?" so I can understand the tradeoff.
- As a premium user, I want to ask "Give me 3 differential picks for this match" so I can build a unique GL team.

## Notifications
- As a premium user, I want a Telegram alert when the playing XI is announced so I can lock my team.
- As a premium user, I want a Telegram alert after the toss so I know the final context for my pick.
- As a user, I want to choose which notification events I receive so I'm not spammed.

## Subscription
- As a free user, I want to see what Premium offers so I can decide if it's worth upgrading.
- As a user, I want to pay for Premium via Razorpay so the process is familiar and secure.
- As a premium user, I want to cancel my subscription at any time so I'm not locked in.

## Admin
- As an admin, I want to retrain models with one API call so I don't need to SSH into servers.
- As an admin, I want to add a new human intelligence rule via the API so I can update knowledge without redeployment.
- As an admin, I want to see prediction accuracy metrics on a dashboard so I can monitor quality.
