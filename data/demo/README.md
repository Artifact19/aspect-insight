# Demo review files (simulated)

These files are for demonstrating the web application. **Every review is simulated.** None is a real customer review, and every row says `(simulated)` in its `source` column. The products, restaurants, hotels and books are well known, and they appear only with traits that are widely reported in public reviews. The reviews are written in the style of real online reviews (mixed opinions, informal wording, dates and star ratings) so that the batch analysis has realistic patterns to find.

Regenerate with `python data/demo/make_demo_reviews.py`. Each file has the columns `review_id, date, source, business, rating, review`, and the web application reads the `review` column.

| Domain | Files |
|---|---|
| Laptop | MacBook Air M3, Dell XPS 13, ASUS ROG Zephyrus G14, Lenovo ThinkPad X1 Carbon |
| Restaurant | Domino's Pizza, Pizza Hut, Starbucks, McDonald's |
| Hotel | The Taj Mahal Palace (Mumbai), Marina Bay Sands (Singapore), ibis |
| Clothing | Levi's 511 jeans, Nike Air Force 1, Uniqlo AIRism T-shirt, Crocs Classic Clog |
| Books | Atomic Habits, The Alchemist, Harry Potter and the Philosopher's Stone, Sapiens |

Each file has 16 or 17 reviews. Suggested pairs for the Compare page: MacBook Air M3 vs Dell XPS 13, Domino's vs Pizza Hut, Taj Mahal Palace vs Marina Bay Sands, Nike Air Force 1 vs Crocs, and Atomic Habits vs The Alchemist.
