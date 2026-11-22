# Demo review files (simulated)

These files are for demonstrating the web application. **Every review is simulated**; none is a real customer review, and every row says `(simulated)` in its `source` column. The restaurant, hotel, kurta, novel and Novix laptop are fictional. The three well-known laptops appear only with traits that are widely reported in public reviews; no defects are invented for real products, so the fictional Novix laptop carries the made-up firmware-update story. They are written in the style of real online reviews (mixed opinions, informal wording, dates, star ratings) so that the batch analysis has realistic patterns to find.

Regenerate with `python data/demo/make_demo_reviews.py`. Each file has the columns `review_id, date, source, business, rating, review`; the web application reads the `review` column.

| File | Domain | Reviews | What the analysis should reveal |
|---|---|---|---|
| `restaurant_saffron_table_koramangala.csv` | Restaurant | 25 | Desserts (tiramisu) and staff are loved; parking complaints; cold pasta complaints appear in November |
| `restaurant_saffron_table_indiranagar.csv` | Restaurant | 25 | Same menu, but slow service and long weekend waits dominate the complaints; rooftop and desserts praised |
| `restaurant_saffron_table_all.csv` | Restaurant | 50 | Both branches together |
| `laptop_novix_aero14.csv` | Laptop | 36 | Battery, screen and keyboard praised; fan noise, two ports, poor webcam and slow support criticised |
| `laptop_novix_aero14_before_update.csv` | Laptop | 23 | September and October: battery is the most praised aspect |
| `laptop_novix_aero14_after_update.csv` | Laptop | 13 | November, after a firmware update: battery becomes the most criticised aspect |
| `laptop_macbook_air_m3.csv` | Laptop | 18 | Battery, silence, weight and trackpad praised; two ports, 60Hz screen, base RAM and upgrade prices criticised |
| `laptop_dell_xps_13.csv` | Laptop | 18 | Display and design praised; touch function row, invisible trackpad, missing headphone jack and price criticised |
| `laptop_asus_rog_zephyrus_g14.csv` | Laptop | 18 | OLED screen and gaming performance praised; fan noise, heat, gaming battery and bundled software criticised |
| `hotel_harbourview_suites.csv` | Hotel | 25 | Location, cleanliness and staff praised; overpriced breakfast, thin walls, slow wifi |
| `clothing_loomline_kurta.csv` | Clothing | 20 | Soft fabric and fit praised; runs small, colour fading and dye bleeding |
| `books_the_salt_archive.csv` | Books | 15 | Characters and writing praised; slow middle and rushed ending |

Suggested demos in the Compare page: the two Saffron Table branches, the Novix laptop before vs after its update, or MacBook Air M3 vs Dell XPS 13.
