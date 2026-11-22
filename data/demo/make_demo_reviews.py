"""Writes the simulated review files used to demonstrate the web application.

Every review was written for demonstration and none is a real customer review. The products, hotels, restaurants and
books are well known, and they appear only with traits that are widely reported in public reviews. Every row of
every file is marked as simulated in the source column. Run: python data/demo/make_demo_reviews.py
"""
import csv
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

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
    ("2026-11", 4, "Plenty of ports including HDMI and USB-A, no dongles needed."),
    ("2026-11", 2, "Coil whine is noticeable in quiet rooms when the GPU is under load."),
    ("2026-11", 5, "Screen, performance and design are all excellent. Best laptop I've owned."),
    ("2026-11", 3, "Fan noise even during light tasks sometimes, silent mode helps a little."),
]

THINKPAD_X1 = [
    ("2026-10", 5, "The keyboard is the best I have ever typed on, deep travel and a lovely feel."),
    ("2026-10", 5, "Incredibly light for a 14 inch laptop, I barely notice it in my backpack."),
    ("2026-10", 4, "Plenty of ports, two Thunderbolt, two USB-A and HDMI, so no dongles at all."),
    ("2026-10", 3, "The display is fine for spreadsheets but looks dull next to an OLED."),
    ("2026-10", 2, "Very expensive for the specs, you are paying a lot for the ThinkPad name."),
    ("2026-10", 4, "Battery gets me through a normal workday of email, Teams and browsing."),
    ("2026-10", 4, "The carbon fibre lid feels sturdy and it survived a fall off my desk."),
    ("2026-10", 3, "Speakers are thin and quiet, fine for calls but not for movies."),
    ("2026-11", 4, "The TrackPoint is handy once you learn it, and the trackpad is smooth too."),
    ("2026-11", 3, "It gets warm on the left side during long video calls."),
    ("2026-11", 5, "Rock solid for work, the fingerprint reader and IR camera log me in instantly."),
    ("2026-11", 2, "Integrated graphics struggle with anything beyond light photo editing."),
    ("2026-11", 4, "Lenovo onsite warranty was excellent, a technician replaced the fan within two days."),
    ("2026-11", 3, "The webcam is sharp but the privacy shutter is easy to leave closed by accident."),
    ("2026-11", 4, "Performance is snappy for office work and coding."),
    ("2026-11", 5, "Professional look, great keyboard and no bloatware. Perfect business laptop."),
]

DOMINOS = [
    ("2026-10", 5, "Delivery arrived in under 30 minutes and the pizza was still hot."),
    ("2026-10", 4, "The Farmhouse pizza is my go to, fresh veggies and a good amount of cheese."),
    ("2026-10", 2, "The base was soggy and there was hardly any cheese on our Margherita."),
    ("2026-10", 4, "The app is easy to use and live tracking tells you exactly when the order will arrive."),
    ("2026-10", 3, "Pizza tastes good but the prices have gone up a lot recently."),
    ("2026-10", 5, "Choco lava cake is still the best dessert on the menu."),
    ("2026-10", 2, "The delivery guy was late by 20 minutes and the garlic bread was cold."),
    ("2026-10", 4, "Weekday offers make it good value for a group of friends."),
    ("2026-11", 3, "The dine in area is small and cramped, better to order home."),
    ("2026-11", 4, "Staff at the counter were quick and polite even on a busy Saturday."),
    ("2026-11", 2, "Toppings were thrown on one side of the pizza and the crust was burnt."),
    ("2026-11", 5, "Cheese burst crust is unbeatable, worth every rupee."),
    ("2026-11", 3, "Customer care took three days to refund a missing item."),
    ("2026-11", 4, "Consistent taste every time, you know exactly what you are getting."),
    ("2026-11", 3, "The sides are overpriced for the tiny portions you get."),
    ("2026-11", 5, "Late night delivery is a lifesaver during exams, always reliable."),
]

PIZZA_HUT = [
    ("2026-10", 5, "The pan pizza is thick, buttery and crispy at the edges, exactly how I like it."),
    ("2026-10", 4, "Nice sit down restaurant feel, good for a family dinner."),
    ("2026-10", 2, "Delivery took over an hour and the pizza arrived lukewarm."),
    ("2026-10", 4, "Generous toppings on the Veggie Supreme and the sauce is tangy."),
    ("2026-10", 3, "Tasty food but it is more expensive than other pizza chains."),
    ("2026-10", 2, "The staff ignored us for 15 minutes before taking our order."),
    ("2026-10", 4, "The garlic bread and pasta were both good, we ordered seconds."),
    ("2026-10", 3, "The pizza was too oily for my taste, the box was soaked."),
    ("2026-11", 5, "Birthday party for my son was handled really well by the manager."),
    ("2026-11", 4, "Clean restaurant and comfortable seating."),
    ("2026-11", 2, "Our order was wrong twice and nobody apologised."),
    ("2026-11", 4, "The combo offers on weekdays are good value."),
    ("2026-11", 3, "The app keeps logging me out and the coupons rarely apply."),
    ("2026-11", 5, "Stuffed crust is amazing, loads of cheese inside."),
    ("2026-11", 3, "Drinks are flat and overpriced, skip them."),
    ("2026-11", 4, "Friendly waiter who suggested a great dessert."),
]

STARBUCKS = [
    ("2026-10", 5, "The caramel macchiato is perfect every single time."),
    ("2026-10", 4, "Cosy ambience and good wifi, my favourite place to work for a few hours."),
    ("2026-10", 2, "Way too expensive for a cup of coffee, almost 400 rupees for a latte."),
    ("2026-10", 4, "Baristas are friendly and always get my name right."),
    ("2026-10", 3, "The coffee is good but the food is dry and overpriced."),
    ("2026-10", 2, "Long queue at peak hours and only one barista on the counter."),
    ("2026-10", 5, "Love the seasonal drinks, the pumpkin spice latte is back."),
    ("2026-10", 4, "Comfortable chairs and plenty of charging points."),
    ("2026-11", 3, "It gets very crowded and noisy in the evenings."),
    ("2026-11", 4, "The cold brew is smooth and strong."),
    ("2026-11", 2, "My frappuccino was watery and far too sweet."),
    ("2026-11", 4, "The app and rewards points make repeat visits worth it."),
    ("2026-11", 3, "Tables are often dirty because staff are too busy to clean them."),
    ("2026-11", 5, "Great location right by the metro, easy to meet friends here."),
    ("2026-11", 4, "The chocolate croissant was warm and flaky."),
    ("2026-11", 3, "Consistent taste, but nothing special for the price."),
]

MCDONALDS = [
    ("2026-10", 4, "Food comes out fast, my order was ready in under five minutes."),
    ("2026-10", 5, "The fries are hot, salty and crispy, still the best fast food fries."),
    ("2026-10", 3, "Cheap and filling, but the burgers are smaller than they used to be."),
    ("2026-10", 2, "The fries were cold and soggy and the burger was squashed."),
    ("2026-10", 4, "The McAloo Tikki is great value for students."),
    ("2026-10", 2, "Tables were sticky and the floor was dirty."),
    ("2026-10", 4, "Self order kiosks make ordering quick and easy."),
    ("2026-10", 3, "The ice cream machine was broken again."),
    ("2026-11", 4, "Happy Meal toys kept my kids busy and the staff were patient with them."),
    ("2026-11", 3, "Delivery was quick but the drink spilled inside the bag."),
    ("2026-11", 5, "Open late and always reliable on a road trip."),
    ("2026-11", 2, "The staff got our order wrong and it took ages to fix."),
    ("2026-11", 4, "The McFlurry is a great treat and the price is fair."),
    ("2026-11", 3, "Taste is consistent but the menu rarely changes."),
    ("2026-11", 4, "Clean washrooms and plenty of seating at this outlet."),
    ("2026-11", 3, "The coffee from McCafe is okay but nothing special."),
]

TAJ_MUMBAI = [
    ("2026-10", 5, "The heritage wing is breathtaking, the grand staircase and the old world decor feel like a museum."),
    ("2026-10", 5, "Our sea facing room had a stunning view of the Gateway of India."),
    ("2026-10", 5, "Service is impeccable, the staff remembered our names from the first day."),
    ("2026-10", 2, "Extremely expensive, even a coffee at the lounge costs a fortune."),
    ("2026-10", 4, "The breakfast spread is huge and the masala dosa was excellent."),
    ("2026-10", 4, "Location is perfect for walking around Colaba and the Fort area."),
    ("2026-10", 3, "The room was lovely but the bathroom fittings felt a little dated."),
    ("2026-10", 4, "The pool is calm and beautiful, a quiet escape from the city noise."),
    ("2026-11", 3, "Check in took almost 40 minutes because of a long queue."),
    ("2026-11", 5, "The bed was so comfortable and the room was spotless."),
    ("2026-11", 4, "Sea Lounge high tea is a must, the scones were fresh and warm."),
    ("2026-11", 2, "The tower wing room was small for the price we paid."),
    ("2026-11", 4, "Security at the entrance is thorough, which made us feel safe."),
    ("2026-11", 3, "The wifi was slow in the room during the evenings."),
    ("2026-11", 5, "Celebrated our anniversary here and the staff surprised us with a cake. Unforgettable."),
    ("2026-11", 4, "Concierge booked us a great heritage walk and a table at a busy restaurant."),
]

MARINA_BAY_SANDS = [
    ("2026-10", 5, "The infinity pool on the 57th floor is unreal, the view of the skyline is worth the trip."),
    ("2026-10", 2, "The pool was so crowded with people taking selfies that we could barely swim."),
    ("2026-10", 4, "Room was spacious with floor to ceiling windows and a great view of Gardens by the Bay."),
    ("2026-10", 2, "Check in queue was over an hour long, terrible for such an expensive hotel."),
    ("2026-10", 3, "Very expensive, you are paying for the pool and the name more than the room."),
    ("2026-10", 4, "Location is excellent, the mall, casino and the light show are right downstairs."),
    ("2026-10", 3, "The room felt a bit tired and dated, the carpet had stains."),
    ("2026-10", 4, "Staff at the concierge were helpful with restaurant bookings."),
    ("2026-11", 5, "The bed was very comfortable and the blackout curtains were perfect after a long flight."),
    ("2026-11", 3, "Breakfast buffet was crowded and the food was average for the price."),
    ("2026-11", 4, "Housekeeping kept the room spotless every day."),
    ("2026-11", 2, "The lifts were always packed and we waited ages to get to our floor."),
    ("2026-11", 4, "Watching the sunset from the rooftop was the highlight of our holiday."),
    ("2026-11", 3, "Room service was slow and very pricey."),
    ("2026-11", 5, "The view from our room at night was spectacular, the city looks magical."),
    ("2026-11", 3, "The bathroom was clean but the water pressure was weak."),
]

IBIS = [
    ("2026-10", 4, "Clean, compact room with everything you need for a short business trip."),
    ("2026-10", 5, "Great value for money, much cheaper than the big hotels nearby."),
    ("2026-10", 3, "The room is very small, there was barely space to open my suitcase."),
    ("2026-10", 4, "The bed was comfortable and I slept really well."),
    ("2026-10", 4, "Staff at the front desk were friendly and check in was quick."),
    ("2026-10", 3, "Breakfast is basic with not many options."),
    ("2026-10", 2, "The walls are thin and I could hear the next room's TV."),
    ("2026-10", 4, "Location is convenient, close to the airport road and the tech park."),
    ("2026-11", 4, "Wifi was fast and free, which is important for work."),
    ("2026-11", 3, "The bathroom is tiny and the shower floods the floor."),
    ("2026-11", 4, "Room was spotless and the towels were fresh every day."),
    ("2026-11", 2, "No room service late at night and the restaurant closes early."),
    ("2026-11", 4, "Simple and modern design, everything works."),
    ("2026-11", 3, "The AC was noisy but it cooled the room well."),
    ("2026-11", 5, "Perfect budget hotel, I stay here every time I visit the city."),
    ("2026-11", 3, "Parking is limited and fills up quickly in the evening."),
]

LEVIS_511 = [
    ("2026-10", 5, "Perfect slim fit, not too tight at the thighs and looks sharp with sneakers."),
    ("2026-10", 4, "The denim is thick and good quality, feels like it will last for years."),
    ("2026-10", 3, "Size runs small at the waist, I had to exchange for one size up."),
    ("2026-10", 4, "The stretch makes them comfortable enough to wear all day."),
    ("2026-10", 2, "The colour faded a lot after just a few washes."),
    ("2026-10", 4, "Classic Levi's look, the dark indigo wash goes with everything."),
    ("2026-10", 3, "Good jeans but expensive compared with other brands."),
    ("2026-10", 5, "My third pair of 511s, the fit is consistent every time."),
    ("2026-11", 2, "The stitching on the back pocket came loose within a month."),
    ("2026-11", 4, "Length was perfect for me, no alteration needed."),
    ("2026-11", 3, "They stretch out and get loose after a full day of wear."),
    ("2026-11", 4, "Bought them on sale and they were great value."),
    ("2026-11", 4, "Delivery was quick and the packaging was neat."),
    ("2026-11", 3, "Bit stiff at first but softened after a couple of washes."),
    ("2026-11", 5, "Comfortable, stylish and durable. Best jeans I own."),
    ("2026-11", 2, "The zip broke after two weeks, very disappointing for the price."),
]

AIR_FORCE_1 = [
    ("2026-10", 5, "Classic clean white look, goes with literally every outfit."),
    ("2026-10", 4, "Leather feels premium and the shoes are very sturdy."),
    ("2026-10", 3, "They run big, I had to go half a size down."),
    ("2026-10", 2, "Creases on the toe box after one week of wearing them."),
    ("2026-10", 4, "Comfortable for walking around town all day."),
    ("2026-10", 3, "Quite heavy compared with running shoes."),
    ("2026-10", 4, "The white gets dirty fast but it's easy to clean with a wipe."),
    ("2026-10", 5, "An iconic sneaker, I get compliments every time I wear them."),
    ("2026-11", 2, "Expensive for a shoe that creases so quickly."),
    ("2026-11", 4, "Good grip on the sole and the cushioning is decent."),
    ("2026-11", 3, "The tongue is stiff and rubs against my ankle."),
    ("2026-11", 4, "Arrived in the original box and looked exactly like the pictures."),
    ("2026-11", 3, "Took about two weeks to break in before they felt comfortable."),
    ("2026-11", 5, "Still looking great after a year of regular wear."),
    ("2026-11", 4, "The laces are long and look good."),
    ("2026-11", 2, "The sole started separating at the heel after a few months."),
]

UNIQLO_AIRISM = [
    ("2026-10", 5, "Super soft and cool on the skin, perfect for the Indian summer."),
    ("2026-10", 4, "The fabric is light and dries very quickly after washing."),
    ("2026-10", 4, "Relaxed fit that looks neat and doesn't cling."),
    ("2026-10", 3, "The fabric is slightly see through in the white colour."),
    ("2026-10", 5, "Great value, I bought five in different colours."),
    ("2026-10", 3, "It wrinkles less than cotton but the neckline stretched a little."),
    ("2026-10", 4, "Sizes are true to fit, the medium fits me perfectly."),
    ("2026-10", 2, "Started pilling under the arms after a month."),
    ("2026-11", 4, "Doesn't smell after a long day, great for travel."),
    ("2026-11", 4, "Simple, minimal design that works for office and casual wear."),
    ("2026-11", 3, "Wish there were more colour options."),
    ("2026-11", 5, "Best basic tee I've owned, I wear one under my shirts every day."),
    ("2026-11", 3, "Feels a bit synthetic compared with pure cotton."),
    ("2026-11", 4, "Online order arrived in two days and the return was easy."),
    ("2026-11", 4, "Holds its shape well even after many washes."),
    ("2026-11", 2, "The colour on the website was much brighter than the shirt I got."),
]

CROCS = [
    ("2026-10", 5, "The most comfortable shoes I've ever worn, like walking on a cushion."),
    ("2026-10", 4, "Light and easy to slip on, perfect for the monsoon."),
    ("2026-10", 3, "Comfortable, but the look is not for everyone."),
    ("2026-10", 4, "Easy to clean, just rinse them with water."),
    ("2026-10", 2, "Very slippery on wet tiles, I almost fell twice."),
    ("2026-10", 3, "Expensive for a pair of rubber clogs."),
    ("2026-10", 4, "Sizes run large, but the heel strap keeps them secure."),
    ("2026-10", 5, "I wear them all day at the hospital and my feet never hurt."),
    ("2026-11", 4, "The Jibbitz charms are fun, my kids love decorating them."),
    ("2026-11", 3, "My feet get sweaty in them on hot days."),
    ("2026-11", 4, "Lots of colour options, I bought the navy and the sage."),
    ("2026-11", 2, "The strap came loose after a few months."),
    ("2026-11", 4, "Durable, my last pair lasted almost three years."),
    ("2026-11", 3, "Not great for long walks, there's no arch support."),
    ("2026-11", 5, "Ugly but so comfortable, I don't care what anyone says."),
    ("2026-11", 4, "Delivery was quick and they were exactly as shown."),
]

ATOMIC_HABITS = [
    ("2026-10", 5, "Practical and easy to apply, I started using habit stacking the next day."),
    ("2026-10", 4, "The idea of getting 1 percent better every day really stuck with me."),
    ("2026-10", 3, "Good ideas, but the book repeats the same points many times."),
    ("2026-10", 5, "Clear writing and great real life examples, I finished it in two days."),
    ("2026-10", 4, "The four laws of behaviour change are simple and memorable."),
    ("2026-10", 2, "Most of it is common sense that could have been a blog post."),
    ("2026-10", 4, "The chapter on identity based habits changed how I think about goals."),
    ("2026-10", 3, "Interesting, but the stories about athletes felt a bit cherry picked."),
    ("2026-11", 5, "The best self help book I've read, I recommend it to everyone."),
    ("2026-11", 4, "Short chapters make it easy to read a little every night."),
    ("2026-11", 3, "The second half drags compared with the first."),
    ("2026-11", 4, "The paperback is well printed and the summary tables at the end are useful."),
    ("2026-11", 2, "Overhyped, I expected more science and less anecdotes."),
    ("2026-11", 4, "Great value, I keep going back to my highlights."),
    ("2026-11", 5, "James Clear explains everything so simply, perfect for beginners."),
    ("2026-11", 3, "A useful book, though the ideas are not really new."),
]

ALCHEMIST = [
    ("2026-10", 5, "A beautiful, inspiring story about following your dreams."),
    ("2026-10", 4, "Simple writing that is easy to read in one sitting."),
    ("2026-10", 2, "Too simplistic and preachy, it reads like a long motivational poster."),
    ("2026-10", 5, "Santiago's journey stayed with me long after I finished it."),
    ("2026-10", 3, "Nice message but the plot is very thin."),
    ("2026-10", 4, "Short and sweet, a good book for teenagers."),
    ("2026-10", 3, "The characters feel more like symbols than real people."),
    ("2026-10", 5, "Every page has a quote worth underlining."),
    ("2026-11", 2, "I don't understand the hype, the ending was predictable."),
    ("2026-11", 4, "The desert setting is described beautifully."),
    ("2026-11", 4, "Paulo Coelho writes like a storyteller, warm and calm."),
    ("2026-11", 3, "Good for a quick read, but not life changing for me."),
    ("2026-11", 4, "The pocket edition is cheap and well printed."),
    ("2026-11", 5, "I reread it every year and find something new each time."),
    ("2026-11", 2, "The spiritual ideas are repeated again and again."),
    ("2026-11", 4, "A fable with a simple but powerful message."),
]

HARRY_POTTER = [
    ("2026-10", 5, "Magical from the first page, Hogwarts feels like a real place."),
    ("2026-10", 5, "Harry, Ron and Hermione are such lovable characters."),
    ("2026-10", 4, "Easy to read and perfect for kids, my daughter finished it in a week."),
    ("2026-10", 3, "The writing is quite simple, it is clearly a children's book."),
    ("2026-10", 4, "The mystery of the stone keeps you guessing until the end."),
    ("2026-10", 5, "Rowling's world building is incredible, every detail is imaginative."),
    ("2026-10", 3, "The Dursley chapters at the start are a bit slow."),
    ("2026-10", 4, "The illustrated edition is gorgeous but heavy."),
    ("2026-11", 5, "Still my favourite book, I've read it more times than I can count."),
    ("2026-11", 4, "Quidditch scenes are fun and exciting."),
    ("2026-11", 3, "The ending feels rushed compared with the rest."),
    ("2026-11", 4, "The paperback is cheap and the print is clear."),
    ("2026-11", 2, "The book arrived with a torn cover and bent pages."),
    ("2026-11", 5, "A perfect introduction to the series, funny and heart warming."),
    ("2026-11", 4, "Dumbledore and Hagrid are wonderful characters."),
    ("2026-11", 3, "Enjoyable, but the later books in the series are much better."),
]

SAPIENS = [
    ("2026-10", 5, "Fascinating, it changed the way I think about human history."),
    ("2026-10", 4, "Harari explains huge ideas in a clear and witty way."),
    ("2026-10", 3, "Interesting, but many claims are oversimplified."),
    ("2026-10", 5, "The chapter on the agricultural revolution blew my mind."),
    ("2026-10", 2, "Too much speculation presented as fact, historians would disagree with a lot of it."),
    ("2026-10", 4, "Easy to read for a non fiction book about history."),
    ("2026-10", 3, "The last part about the future drags and feels off topic."),
    ("2026-10", 4, "The idea that shared myths let humans cooperate is brilliant."),
    ("2026-11", 4, "The hardcover is well made and the illustrations are helpful."),
    ("2026-11", 2, "Very long and repetitive in the middle sections."),
    ("2026-11", 5, "One of the most thought provoking books I've ever read."),
    ("2026-11", 3, "Good overview, but the author's opinions creep in everywhere."),
    ("2026-11", 4, "Great value, I learned more from this than from school history."),
    ("2026-11", 3, "The writing is engaging but some chapters are dense."),
    ("2026-11", 5, "Perfect for curious readers, I keep recommending it."),
    ("2026-11", 4, "The structure from cognitive to scientific revolution makes it easy to follow."),
]

SOURCES = {"Restaurant": ["Google", "Zomato"], "Laptop": ["Online store", "Retail site"],
           "Hotel": ["Google", "Booking site"], "Clothing": ["Online store"], "Books": ["Online store", "Goodreads-style site"]}

FILES = [
    ("laptop_macbook_air_m3", "Laptop", "Apple MacBook Air 13 (M3)", MACBOOK_AIR),
    ("laptop_dell_xps_13", "Laptop", "Dell XPS 13", DELL_XPS13),
    ("laptop_asus_rog_zephyrus_g14", "Laptop", "ASUS ROG Zephyrus G14", ZEPHYRUS_G14),
    ("laptop_lenovo_thinkpad_x1_carbon", "Laptop", "Lenovo ThinkPad X1 Carbon", THINKPAD_X1),
    ("restaurant_dominos", "Restaurant", "Domino's Pizza", DOMINOS),
    ("restaurant_pizza_hut", "Restaurant", "Pizza Hut", PIZZA_HUT),
    ("restaurant_starbucks", "Restaurant", "Starbucks", STARBUCKS),
    ("restaurant_mcdonalds", "Restaurant", "McDonald's", MCDONALDS),
    ("hotel_taj_mahal_palace_mumbai", "Hotel", "The Taj Mahal Palace, Mumbai", TAJ_MUMBAI),
    ("hotel_marina_bay_sands", "Hotel", "Marina Bay Sands, Singapore", MARINA_BAY_SANDS),
    ("hotel_ibis", "Hotel", "ibis (budget hotel)", IBIS),
    ("clothing_levis_511_jeans", "Clothing", "Levi's 511 Slim Jeans", LEVIS_511),
    ("clothing_nike_air_force_1", "Clothing", "Nike Air Force 1", AIR_FORCE_1),
    ("clothing_uniqlo_airism_tshirt", "Clothing", "Uniqlo AIRism T-shirt", UNIQLO_AIRISM),
    ("clothing_crocs_classic_clog", "Clothing", "Crocs Classic Clog", CROCS),
    ("books_atomic_habits", "Books", "Atomic Habits (James Clear)", ATOMIC_HABITS),
    ("books_the_alchemist", "Books", "The Alchemist (Paulo Coelho)", ALCHEMIST),
    ("books_harry_potter_philosophers_stone", "Books", "Harry Potter and the Philosopher's Stone", HARRY_POTTER),
    ("books_sapiens", "Books", "Sapiens (Yuval Noah Harari)", SAPIENS),
]


def rows(items, domain, entity, rng, start):
    out = []
    for i, (month, rating, text) in enumerate(items):
        day = rng.randint(1, 28)
        out.append({"review_id": f"{domain[:3].upper()}-{start + i + 1:04d}", "date": f"{month}-{day:02d}",
                    "source": f"{rng.choice(SOURCES[domain])} (simulated)", "business": entity, "rating": rating,
                    "review": text})
    return sorted(out, key=lambda r: r["date"])


def write(name, data):
    with (HERE / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)
    print(f"{name}.csv: {len(data)} reviews")


def main():
    rng = random.Random(7)
    for old in HERE.glob("*.csv"):
        old.unlink()
    for i, (name, domain, entity, items) in enumerate(FILES):
        write(name, rows(items, domain, entity, rng, start=100 * (i + 1)))


if __name__ == "__main__":
    main()
