# Synthetic Neutral pairs

Generator and verifier: `Qwen/Qwen2.5-7B-Instruct`, temperature 0.9, 4 real Neutral examples per request.

| Step | Sentences |
|---|---|
| generated | 3,000 |
| rejected: aspect missing | 178 |
| rejected: duplicate | 42 |
| rejected: not English | 227 |
| passed format filters | 2,553 |
| verified neutral | 1,705 |
| rejected by verifier | 848 |

| Domain | Real Neutral (train) | Synthetic, verified | Synthetic, format filters only |
|---|---|---|---|
| Books | 86 | 268 | 439 |
| Clothing | 46 | 165 | 311 |
| Hotel | 19 | 334 | 538 |
| Laptop | 220 | 392 | 555 |
| Restaurant | 84 | 546 | 710 |

## Examples (verified)

- *Restaurant*, aspect **atmosphere**: The atmosphere is just average , neither too cozy nor overly crowded .
- *Hotel*, aspect **snacks**: The selection of snacks was adequate , offering a few options for late - night munching .
- *Restaurant*, aspect **staff**: The staff seemed friendly enough , but there wasn ' t anything particularly noteworthy about their service .
- *Hotel*, aspect **street parking**: Street parking is available , though it can be a bit challenging during busy times .
- *Restaurant*, aspect **Customer service**: The customer service was standard , offering help when needed without being overly attentive .
- *Restaurant*, aspect **satay skewers**: The satay skewers were alright , with a decent blend of flavors , though not particularly outstanding .
- *Restaurant*, aspect **service**: The service was acceptable , neither particularly fast nor slow .
- *Restaurant*, aspect **service**: The service was adequate , neither particularly welcoming nor unfriendly .
- *Restaurant*, aspect **little dive bar**: The place is a little dive bar , so don ' t expect five - star conditions but it works for what it is .
- *Books*, aspect **Kathy**: Kathy was portrayed as a dedicated detective , which was an acceptable but unremarkable characterization .
- *Laptop*, aspect **email**: the email client works adequately , allowing me to send and receive messages without any issues .
- *Hotel*, aspect **apartment**: The apartment was adequately furnished , though not particularly distinctive .
- *Restaurant*, aspect **texture**: The texture of the pasta was al dente , as usual .
- *Clothing*, aspect **moc**: The moc boots have a traditional look , which is what I was expecting .
- *Books*, aspect **book**: The book provides a comprehensive overview of the subject without particularly standing out from others in its field .

## Examples rejected by the verifier

- *Laptop*, aspect **re - set button**, verifier: positive: the re - set button is located on the left side of the laptop , next to the battery compartment , and functions as expected .
- *Clothing*, aspect **style**, verifier: positive: The style is straightforward and classic , nothing too flashy but still noticeable .
- *Restaurant*, aspect **vegetable bao**, verifier: positive: The vegetable bao had just enough seasoning , neither overly salty nor bland .
- *Hotel*, aspect **hosts**, verifier: positive: The hosts were polite and available when needed , but nothing exceptional .
- *Books*, aspect **accounts**, verifier: negative: The accounts of the events , while detailed , do not offer any novel insights into the situation .
- *Hotel*, aspect **loft**, verifier: positive: The loft provided enough height for us to move around without bumping our heads , which was an acceptable feature .
- *Clothing*, aspect **size**, verifier: positive: The size was just right for my usual fit .
- *Laptop*, aspect **asus flip**, verifier: positive: asus flip comes with a standard backlit keyboard , which is convenient for typing in low - light conditions .
