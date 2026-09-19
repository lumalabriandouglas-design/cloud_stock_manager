# Phone app for this shop (not built)

If a client wants “an app for the website”, they should **not** get a second shop.

## The rule

One business = one login = one list of products and sales.

The website and the app are two doors into the **same** book on Railway.

```
Phone app  ──┐
             ├── same account ──► same shop data
Website    ──┘
```

Sell 3 soaps on the phone → inventory on the computer already shows 3 less.  
Add stock on the computer → the phone sees it when it opens.

## How (when we build it)

- Same email / Google sign-in
- App talks to this website’s data (API), no extra database
- If they are offline, queue the sale on the phone, then send it when network returns — still one shop, not a copy

## What we do not do

- Do not make a new Postgres for the app
- Do not ask them to type products twice
- Do not let the app and website disagree
