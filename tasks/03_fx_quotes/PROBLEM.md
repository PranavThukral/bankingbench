# Ticket: quote a synthetic currency transfer

`fx.quote.quote_transfer(amount_minor:int,src:str,dst:str,rates:dict[tuple[str,str],Decimal],fee_bps:int)`
returns frozen `Quote(fee_minor:int,converted_minor:int,rate_used:Decimal,path:tuple[str,...])`.
Expose `RateUnavailable(ValueError)` for unavailable currencies/pairs.

Minor units: CAD/USD/EUR/GBP=2, JPY=0, KWD/BHD=3. Rates are positive finite Decimals in
destination major units per source major unit. All money values returned are int minor units.
Amount is nonnegative int, never bool; fee_bps integer in [0,10000]; invalid values -> ValueError.
Inputs use distinct src/dst; an unsupported currency -> RateUnavailable.

1. Fee in source minor units = amount_minor × fee_bps / 10000, rounded HALF_EVEN to integer.
   Deduct this fee BEFORE conversion. Returned fee_minor is this source fee.
2. Use direct `(src,dst)` rate if present, path `(src,dst)`. Otherwise require both `(src,"USD")`
   and `("USD",dst)`, multiply at full precision, path `(src,"USD",dst)`. Do not infer inverses or
   other routes. Missing required rates -> RateUnavailable. Direct rate takes precedence.
3. Convert net source minor units to source major units, apply the full rate, then scale to
   destination minor units. Round ONLY the final destination amount HALF_EVEN to integer.
   Do not round the USD leg of a cross quote. rate_used is the full direct/product Decimal.

Do not mutate rates. Zero amount returns zero amounts while still resolving the declared route.
No actual currency market or customer is represented. Run `python -m pytest tests -q` from starter.
