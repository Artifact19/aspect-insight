"""Writes the simulated review files used to demonstrate the web application.

Every review was written for demonstration; none is a real customer review. The restaurant, hotel, kurta, novel and
the Novix laptop are fictional. The three well-known laptops (MacBook Air M3, Dell XPS 13, ASUS ROG Zephyrus G14)
appear only with traits that are widely reported in public reviews; no defects are invented for real products, and
every row of every file is marked as simulated in the source column. Run: python data/demo/make_demo_reviews.py
"""
import csv
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

RESTAURANT = {
    "Koramangala": [
        ("2026-10", 5, "Came here for my sister's birthday and the tiramisu was honestly the best I've had in Bangalore. Staff were warm and quick."),
        ("2026-10", 4, "Lovely ambience, soft lighting and not too loud. The mushroom risotto was creamy and well seasoned. Parking was a nightmare though."),
        ("2026-10", 5, "Excellent service, our server Ravi recommended the lamb shank and it was perfect. Will be back."),
        ("2026-10", 4, "Food is great and prices are fair for the portion size. Only complaint is there's no proper parking nearby."),
        ("2026-10", 3, "Pasta was decent, nothing special. Desserts made up for it though, the panna cotta was lovely."),
        ("2026-10", 5, "Cozy place, great music, and the staff remembered us from last time. Best date night spot in Koramangala."),
        ("2026-10", 4, "Pizza crust was thin and crispy, toppings were fresh. Drinks a bit overpriced."),
        ("2026-10", 2, "Had to circle the block 20 mins for parking. Food was good but the whole experience started on a bad note."),
        ("2026-10", 5, "The chocolate fondant is to die for. Service was attentive without being pushy."),
        ("2026-10", 4, "Good vegetarian options, the pesto gnocchi was a highlight. Wine list is limited."),
        ("2026-10", 5, "Booked for a team dinner of 12 and they handled it really well. Food came out together and hot."),
        ("2026-10", 3, "Ambience is nice but the AC was way too cold. Food was ok."),
        ("2026-10", 4, "Value for money, especially the weekday lunch combo. Desserts are a must."),
        ("2026-11", 5, "Still my favourite italian place. Tiramisu never disappoints and the staff are always friendly."),
        ("2026-11", 2, "The pasta came out lukewarm and the sauce had gone gluey. Told the waiter, he apologised but nothing was done."),
        ("2026-11", 4, "Great atmosphere and lovely staff. The carbonara was slightly cold when it arrived but tasted good."),
        ("2026-11", 4, "Prices went up a bit this month but quality is still good. Loved the new seasonal soup."),
        ("2026-11", 3, "Penne arrebiata was cold in the middle, like it was reheated. Desserts still great."),
        ("2026-11", 5, "Beautiful decor for the festive season. Service was super quick even on a Saturday."),
        ("2026-11", 4, "Bruschetta and the house salad were fresh. Parking still a pain, use the mall basement."),
        ("2026-11", 2, "Two of our pastas were cold. Manager comped dessert which was nice, but kitchen needs to fix this."),
        ("2026-11", 5, "Celebrated our anniversary here, the staff brought a candle on the dessert without us asking. So sweet."),
        ("2026-11", 4, "Solid food, friendly staff, reasonable bill. The garlic bread is addictive."),
        ("2026-11", 3, "Food is fine but the place is getting crowded and noisy on weekends."),
        ("2026-11", 5, "Hands down the best desserts in the area. The tiramisu and the lemon tart are both incredible."),
    ],
    "Indiranagar": [
        ("2026-10", 3, "Food was good but we waited 40 minutes for our mains on a Saturday night. Nobody told us why."),
        ("2026-10", 4, "Lovely interiors and the rooftop seating is beautiful. Service was slow but the pizza was worth it."),
        ("2026-10", 2, "Waited 25 minutes just to place our order. The waiter seemed overwhelmed. Tiramisu was good though."),
        ("2026-10", 5, "Weekday lunch was quick and the food was delicious. Great spot for a work lunch."),
        ("2026-10", 3, "Ambience is gorgeous but service is painfully slow on weekends. Had to ask three times for water."),
        ("2026-10", 4, "Risotto was rich and flavourful, desserts were excellent. Bit pricey but fine for a special occasion."),
        ("2026-10", 2, "Booked a table for 8pm, got seated at 8:35. Staff were polite but clearly understaffed."),
        ("2026-10", 4, "The rooftop view at sunset is lovely. Drinks were good, food average."),
        ("2026-10", 1, "Worst service ever. Order took over an hour, half of it came wrong and the bill had extra items."),
        ("2026-10", 5, "The lasagna was amazing and the staff were super friendly. Came on a Tuesday, no wait at all."),
        ("2026-10", 3, "Nice place, decent food, but waiting 30 mins for a table even with a reservation is not ok."),
        ("2026-10", 4, "Panna cotta and tiramisu both brilliant. Main course was ok."),
        ("2026-11", 2, "Again a long wait on Sunday. Food is good but I'm not sure it's worth the 45 minute delay."),
        ("2026-11", 3, "Pizza was tasty but the waiter forgot our drinks twice. Weekend service needs serious improvement."),
        ("2026-11", 4, "Loved the ambience and the music. Gnocchi was soft and the sauce was perfect."),
        ("2026-11", 2, "Our pasta was cold and it took forever to arrive. Expected better at this price."),
        ("2026-11", 5, "Came on a weekday, service was quick and the food was spot on. The tiramisu is a must try."),
        ("2026-11", 1, "Waited 50 mins, food arrived cold, and nobody apologised. Not coming back on a weekend."),
        ("2026-11", 4, "Prices are reasonable for Indiranagar. The rooftop is the best part."),
        ("2026-11", 3, "Decent food, great desserts, terrible wait times on Saturday."),
        ("2026-11", 2, "Staff are polite but there just aren't enough of them. Took 20 mins to get the bill."),
        ("2026-11", 4, "The new menu has some great additions, loved the truffle fries. Service a bit slow as usual."),
        ("2026-11", 3, "Lovely decor, average pasta, very slow service. Desserts are the only reason I'd return."),
        ("2026-11", 5, "Hosted a small birthday on the rooftop, staff decorated the table and the cake was delicious."),
        ("2026-11", 2, "45 minute wait for two pizzas. The pizza was good but the experience was frustrating."),
    ],
}

LAPTOP = [
    ("2026-09", 5, "Battery life is insane, I get a full workday of coding and meetings on one charge."),
    ("2026-09", 4, "The screen is bright and sharp, great for working outdoors. Only two USB-C ports though, had to buy a dongle."),
    ("2026-09", 5, "Keyboard is a joy to type on, nice travel and quiet. Build feels premium for the price."),
    ("2026-09", 4, "Super light, I carry it everywhere. Webcam is grainy in low light which is annoying for calls."),
    ("2026-09", 3, "Good laptop but the fan gets loud when compiling or gaming. Normal use is silent."),
    ("2026-09", 5, "Setup took five minutes and it boots in seconds. Battery easily lasts 12 hours."),
    ("2026-09", 2, "Customer support took 9 days to reply about a dead pixel. The laptop itself is fine."),
    ("2026-09", 4, "Speakers are surprisingly loud and clear. Trackpad is smooth and precise."),
    ("2026-09", 4, "Great value compared to similar ultrabooks. Display colours are accurate for photo editing."),
    ("2026-09", 3, "Performance is good for office work but it throttles under heavy load and the bottom gets hot."),
    ("2026-09", 5, "Battery and screen are both excellent. Best laptop I've owned."),
    ("2026-09", 4, "The aluminium body feels solid. Wish it had an HDMI port."),
    ("2026-10", 5, "Still getting 11-12 hours of battery after a month. Keyboard backlight is nice too."),
    ("2026-10", 4, "Fast SSD, apps open instantly. Fan noise under load is the only real downside."),
    ("2026-10", 2, "Webcam is honestly terrible, everyone on zoom says I look blurry. Rest of the laptop is good."),
    ("2026-10", 4, "Screen is gorgeous but very reflective in bright rooms."),
    ("2026-10", 3, "Decent machine. Only two ports is really limiting for a work laptop."),
    ("2026-10", 5, "Charges from 0 to 70 percent in about 45 minutes, very handy when travelling."),
    ("2026-10", 1, "Hinge started creaking after three weeks and support keeps asking me to reinstall windows."),
    ("2026-10", 4, "Lightweight and stylish. Speakers are good for movies. Price is a bit high."),
    ("2026-10", 5, "Perfect college laptop. Battery lasts through all my lectures and it fits in a small bag."),
    ("2026-10", 3, "The trackpad sometimes registers palm touches while typing. Otherwise happy."),
    ("2026-10", 4, "Keyboard and screen are top notch. Fan could be quieter."),
    ("2026-11", 2, "Since the BIOS update 1.0.7 the battery drains overnight even when the lid is closed. Very disappointing."),
    ("2026-11", 2, "Battery life dropped to around 5 hours after the latest firmware update. It used to be 12."),
    ("2026-11", 3, "Good laptop overall but battery has gotten worse after the November update."),
    ("2026-11", 1, "Laptop wakes up in my bag and gets hot, battery dead by morning. Support says a fix is 'coming soon'."),
    ("2026-11", 4, "Display is still the best part, colours are vivid. Battery not as good as before the update though."),
    ("2026-11", 2, "Battery used to be great, now it barely lasts half a day. Rolling back the BIOS fixed it partially."),
    ("2026-11", 5, "Keyboard, screen, weight, all excellent. Haven't installed the update yet so battery is still great."),
    ("2026-11", 3, "Fan noise is still the main issue for me, and the webcam is poor. Battery ok."),
    ("2026-11", 2, "Support chat was useless, they just sent me a generic article about battery saver mode."),
    ("2026-11", 4, "Love the build quality and the screen. Would be perfect with one more USB port."),
    ("2026-11", 2, "Sleep mode is broken after the update and the battery drains in my bag. Please fix this."),
    ("2026-11", 4, "Speakers and display make it great for netflix. Performance is smooth for daily use."),
    ("2026-11", 3, "Keyboard is great but the battery is now average after the update."),
]

HOTEL = [
    ("2026-10", 5, "Room was spotless and the sea view from the balcony was stunning. Staff at the front desk were lovely."),
    ("2026-10", 4, "Great location, five minutes walk to the beach. Breakfast spread was good but overpriced at 900 per person."),
    ("2026-10", 3, "Clean rooms and friendly staff, but the walls are thin and we could hear the next room all night."),
    ("2026-10", 5, "The pool is beautiful and never crowded. Housekeeping was quick and thorough."),
    ("2026-10", 4, "Comfortable bed, strong AC, good shower pressure. Wifi was slow in the evenings."),
    ("2026-10", 2, "Wifi barely worked and the room smelled damp. Location is the only good thing."),
    ("2026-10", 5, "Staff went out of their way to arrange an early check-in after our night flight. Excellent service."),
    ("2026-10", 4, "Rooms are spacious and tastefully done. Restaurant food is average."),
    ("2026-10", 3, "Nice property but breakfast was repetitive over four days and quite expensive."),
    ("2026-10", 5, "Perfect location, lovely staff, clean room. Would definitely stay again."),
    ("2026-10", 3, "The room was clean but tiny for the price. Bathroom was nicely done."),
    ("2026-10", 4, "Rooftop bar has an amazing sunset view. Drinks are pricey."),
    ("2026-10", 2, "Noise from the street and the bar kept us awake till 1am. Ask for a room away from the road."),
    ("2026-10", 4, "Check in was smooth and the staff were warm. The gym is small but has what you need."),
    ("2026-11", 5, "Housekeeping left towel animals and a note for my daughter, she loved it. Fantastic staff."),
    ("2026-11", 3, "Location is great but the wifi is a joke, couldn't take a single video call."),
    ("2026-11", 4, "Pool and spa were relaxing. Breakfast still overpriced for what you get."),
    ("2026-11", 2, "Our room had a broken AC for two nights and it took a day to fix. Staff were apologetic."),
    ("2026-11", 5, "Spotless room, comfy bed, beautiful view. Worth every rupee."),
    ("2026-11", 3, "Decent stay. Walls are thin and the hallway is noisy late at night."),
    ("2026-11", 4, "Great value in the off season. Staff are the highlight, so helpful."),
    ("2026-11", 4, "Parking was easy and the beach is right there. Room service was slow."),
    ("2026-11", 5, "Best hotel we stayed at on our trip. Clean, friendly, great location."),
    ("2026-11", 2, "Overpriced for the room size and the bathroom drain was blocked. Location is good though."),
    ("2026-11", 4, "Lovely balcony and sea breeze. The restaurant's fish curry was excellent."),
]

CLOTHING = [
    ("2026-10", 5, "The cotton is so soft and breathable, perfect for Chennai heat. Colour is exactly as pictured."),
    ("2026-10", 3, "Nice fabric but it runs small, I had to exchange for one size up."),
    ("2026-10", 4, "Stitching is neat and the embroidery looks premium. Delivery was quick."),
    ("2026-10", 2, "Colour faded noticeably after just two washes. Disappointed."),
    ("2026-10", 4, "Fits well and the length is perfect. Fabric is a little thin, needs an inner."),
    ("2026-10", 5, "Got so many compliments at the office. Great quality for the price."),
    ("2026-10", 3, "Sleeves are too tight, otherwise a lovely kurta."),
    ("2026-10", 4, "Comfortable for daily wear and doesn't wrinkle much. Buttons feel a bit cheap."),
    ("2026-10", 1, "Received a different colour than ordered and the return process took two weeks."),
    ("2026-10", 5, "Second purchase from this brand, the fit and fabric are consistently good."),
    ("2026-11", 2, "The dye bled onto my other clothes in the first wash. Wash separately!"),
    ("2026-11", 4, "Soft fabric, good fit, pockets are a nice touch. Size chart is accurate this time."),
    ("2026-11", 3, "Pretty print but the colour is duller than the photos."),
    ("2026-11", 5, "Lightweight and elegant, perfect for festive season. Delivered in 2 days."),
    ("2026-11", 2, "Runs very small and the fabric shrank after washing."),
    ("2026-11", 4, "Good quality cotton and the stitching has held up after many washes."),
    ("2026-11", 3, "Fit is fine but the neckline is a bit too deep for office wear."),
    ("2026-11", 4, "Value for money. Colour stayed fine for me after cold wash."),
    ("2026-11", 5, "Absolutely love it, the fabric feels luxurious and the fit is flattering."),
    ("2026-11", 2, "Thread came loose at the hem within a week. Quality control needs work."),
]

BOOKS = [
    ("2026-10", 5, "The characters are wonderfully written, especially the grandmother. I couldn't put it down."),
    ("2026-10", 3, "Beautiful prose but the middle section drags for almost a hundred pages."),
    ("2026-10", 4, "The author clearly did her research on the salt trade, the historical detail is fascinating."),
    ("2026-10", 2, "Too slow for me. The plot only picks up in the last fifty pages."),
    ("2026-10", 5, "A gripping, emotional story. The ending made me cry."),
    ("2026-10", 4, "Lovely writing and a clever structure with letters between chapters. Ending felt a bit rushed."),
    ("2026-10", 3, "Interesting premise, but too many minor characters to keep track of."),
    ("2026-11", 5, "One of the best novels I've read this year. The dialogue feels so real."),
    ("2026-11", 2, "The ending was rushed and left too many questions unanswered."),
    ("2026-11", 4, "Atmospheric and moving. The pacing is slow but it suits the story."),
    ("2026-11", 3, "Good book, but the paperback binding started coming apart after one read."),
    ("2026-11", 5, "The relationship between the two sisters is the heart of the book and it is beautifully done."),
    ("2026-11", 4, "Rich historical setting, memorable characters. Could have been 80 pages shorter."),
    ("2026-11", 3, "The translation feels clunky in places but the story is strong."),
    ("2026-11", 5, "Gorgeous cover and an even better story. Highly recommend."),
]

MACBOOK_AIR = [
    ("2026-10", 5, "Battery life is unreal, I go two full days of college without charging."),
    ("2026-10", 5, "Completely silent since there's no fan, and it never gets uncomfortably hot on my lap."),
    ("2026-10", 4, "The display is sharp and colour accurate, but it's only 60Hz which feels dated at this price."),
    ("2026-10", 3, "Only two USB-C ports, so I'm living the dongle life again."),
    ("2026-10", 5, "Super light and thin, easily the best laptop for travelling."),
    ("2026-10", 4, "Keyboard is comfortable and the trackpad is the best I've used on any laptop."),
    ("2026-10", 2, "The base model with 8GB RAM struggles with many chrome tabs and Lightroom. Upgrades are very expensive."),
    ("2026-10", 4, "Speakers are surprisingly full for such a thin machine. Webcam is clear on video calls."),
    ("2026-11", 3, "Performance drops during long video exports because there's no fan to cool it."),
    ("2026-11", 5, "Build quality is excellent, the aluminium body feels premium and solid."),
    ("2026-11", 2, "Gaming options on macOS are very limited, most of my steam library doesn't run."),
    ("2026-11", 4, "Great value when it's on sale, but the storage and memory upgrade prices are ridiculous."),
    ("2026-11", 4, "The notch in the screen bothered me at first but I stopped noticing it after a week."),
    ("2026-11", 5, "Wakes instantly, apps open fast, and the battery barely moves while browsing."),
    ("2026-11", 4, "Driving two external monitors with the lid closed works well for my desk setup."),
    ("2026-11", 3, "Lovely laptop but the price in India is steep for the base configuration."),
    ("2026-11", 5, "MagSafe charging is so convenient, and the charger is tiny."),
    ("2026-11", 4, "Perfect for coding and writing. Just wish it had an HDMI port."),
]

DELL_XPS13 = [
    ("2026-10", 5, "The OLED display is stunning, colours pop and text is razor sharp."),
    ("2026-10", 3, "The touch function row looks cool but I keep hitting it by accident and miss physical keys."),
    ("2026-10", 4, "Gorgeous design, the glass palm rest and slim bezels make it look very premium."),
    ("2026-10", 2, "The invisible haptic trackpad is hard to use, I can't feel where it starts and ends."),
    ("2026-10", 3, "Only two USB-C ports and no headphone jack, which is a strange choice for a work laptop."),
    ("2026-10", 4, "Battery easily lasts a full workday of documents and browsing."),
    ("2026-10", 4, "Keyboard is edge to edge and nice to type on once you get used to the flat keys."),
    ("2026-10", 3, "It gets warm under load and the fan becomes noticeable during video calls."),
    ("2026-11", 5, "Very compact and light, fits in any bag. Great for travel."),
    ("2026-11", 3, "Webcam is average, fine for meetings but nothing special."),
    ("2026-11", 4, "Speakers are clear and loud enough for a small room."),
    ("2026-11", 2, "Too expensive for what you get, similar specs are much cheaper elsewhere."),
    ("2026-11", 4, "Performance is snappy for office work and light photo editing."),
    ("2026-11", 3, "The screen is glossy and quite reflective near windows."),
    ("2026-11", 5, "Build quality is excellent, the aluminium chassis feels rock solid."),
    ("2026-11", 4, "Dell support was quick to arrange a home visit for a loose key."),
    ("2026-11", 3, "Battery drops quickly with the OLED at full brightness."),
    ("2026-11", 4, "Lovely machine overall, but the missing headphone jack still annoys me."),
]

ZEPHYRUS_G14 = [
    ("2026-10", 5, "The 120Hz OLED screen is the best I've seen on a gaming laptop, games look incredible."),
    ("2026-10", 5, "Runs every game I play at high settings, the RTX 4070 is a beast in this small body."),
    ("2026-10", 3, "Fans get really loud when gaming, you need headphones."),
    ("2026-10", 4, "Aluminium build feels premium and it's compact enough to carry to college."),
    ("2026-10", 2, "Battery life while gaming is barely an hour and a half."),
    ("2026-10", 4, "For browsing and notes the battery lasts around 7 hours, which is decent for a gaming laptop."),
    ("2026-10", 3, "The bottom gets very hot during long gaming sessions."),
    ("2026-10", 4, "Speakers are punchy and loud, surprisingly good for a laptop."),
    ("2026-11", 2, "Armoury Crate software is bloated and keeps popping up notifications."),
    ("2026-11", 4, "Keyboard is comfortable with nice per-key lighting."),
    ("2026-11", 3, "Expensive, but you're paying for a thin gaming laptop with a great screen."),
    ("2026-11", 5, "Perfect mix of portability and power. Video editing in Premiere is smooth."),
    ("2026-11", 3, "The charger brick is big and heavy, which ruins the portability a bit."),
    ("2026-11", 4, "Trackpad is large and smooth. Webcam is only okay."),
    ("2026-11", 4, "Plenty of ports including HDMI and USB-A, no dongles needed."),
    ("2026-11", 2, "Coil whine is noticeable in quiet rooms when the GPU is under load."),
    ("2026-11", 5, "Screen, performance and design are all excellent. Best laptop I've owned."),
    ("2026-11", 3, "Fan noise even during light tasks sometimes, silent mode helps a little."),
]

SOURCES = {"Restaurant": ["Google", "Zomato"], "Laptop": ["Online store", "Retail site"],
           "Hotel": ["Google", "Booking site"], "Clothing": ["Online store"], "Books": ["Online store", "Goodreads-style site"]}


def rows(items, domain, entity, rng, start=0):
    out = []
    for i, (month, rating, text) in enumerate(items):
        day = rng.randint(1, 28)
        out.append({"review_id": f"{domain[:3].upper()}-{start + i + 1:04d}", "date": f"{month}-{day:02d}",
                    "source": f"{rng.choice(SOURCES[domain])} (simulated)", "business": entity, "rating": rating,
                    "review": text})
    return sorted(out, key=lambda r: r["date"])


def write(name, data):
    with (HERE / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)
    print(f"{name}: {len(data)} reviews")


def main():
    rng = random.Random(152)
    kor = rows(RESTAURANT["Koramangala"], "Restaurant", "Saffron Table, Koramangala", rng)
    ind = rows(RESTAURANT["Indiranagar"], "Restaurant", "Saffron Table, Indiranagar", rng, start=len(kor))
    write("restaurant_saffron_table_koramangala.csv", kor)
    write("restaurant_saffron_table_indiranagar.csv", ind)
    write("restaurant_saffron_table_all.csv", sorted(kor + ind, key=lambda r: r["date"]))
    lap = rows(LAPTOP, "Laptop", "Novix Aero 14", rng)
    write("laptop_novix_aero14.csv", lap)
    write("laptop_novix_aero14_before_update.csv", [r for r in lap if r["date"] < "2026-11"])
    write("laptop_novix_aero14_after_update.csv", [r for r in lap if r["date"] >= "2026-11"])
    write("laptop_macbook_air_m3.csv", rows(MACBOOK_AIR, "Laptop", "Apple MacBook Air 13 (M3)", rng, start=100))
    write("laptop_dell_xps_13.csv", rows(DELL_XPS13, "Laptop", "Dell XPS 13", rng, start=200))
    write("laptop_asus_rog_zephyrus_g14.csv", rows(ZEPHYRUS_G14, "Laptop", "ASUS ROG Zephyrus G14", rng, start=300))
    write("hotel_harbourview_suites.csv", rows(HOTEL, "Hotel", "Harbourview Suites, Goa", rng))
    write("clothing_loomline_kurta.csv", rows(CLOTHING, "Clothing", "Loomline cotton kurta", rng))
    write("books_the_salt_archive.csv", rows(BOOKS, "Books", "The Salt Archive (novel)", rng))


if __name__ == "__main__":
    main()
