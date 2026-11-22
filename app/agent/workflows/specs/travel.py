from app.agent.workflows.spec import Workflow as W

M = "travel"
_DATES = ("Resolve the date from today; if it is vague ('next week', 'early December') ask with ask_choice("
          "topic='flight', kind='date') offering 3-5 concrete dates as YYYY-MM-DD values with labels like "
          "'Mon 30 Nov'.")
_AFTER = ("After approval Purser never takes payment: never say the ticket is paid or issued. If the search source "
          "is 'sample', say these are estimated fares.")
WORKFLOWS = [
    W("flight_search", M, "Find flights: 'I have to go to Mumbai next week', 'flights to Delhi on 3rd', 'Pune se "
      "Delhi'. Also picking the date or a flight from the list shown.",
      ("get_my_location", "search_flights", "find_people"),
      ("Origin: the city named, else get_my_location and say it back. Never assume an origin city: if it is still "
       "unknown, ask for it (in words if ask_choice is used up).", _DATES, "Call search_flights.",
       "Speak the count, the cheapest and the fastest (airline, time, price), then ask which one to book. Never "
       "invent a flight, time or fare."), required=("search_flights",)),
    W("book_flight", M, "Book a flight from the list: 'book the cheapest', 'the 9:25 one', 'option 3'.",
      ("search_flights", "propose_flight_booking"),
      ("Use the search_id and option id from 'Last flight search shown' in the Situation; call search_flights only "
       "if there is none.", "Call propose_flight_booking with that search_id and option id.", "Read 'say'; ask; stop.",
       _AFTER)),
    W("trip", M, "A whole trip with a hotel, or a hotel: 'plan my Mumbai trip 24 to 26', 'flight and hotel', "
      "'hotel bhi chahiye', 'book both', or booking for someone else ('book Rahul's trip').",
      ("get_my_location", "search_flights", "search_hotels", "propose_trip_booking", "propose_flight_booking",
       "find_people"),
      ("Never assume an origin city; use the one named earlier in the Situation, else ask.",
       "Reuse the flight / hotel search_id from the Situation when it matches the route and dates; otherwise "
       "search_flights for the outbound day and search_hotels for the stay (check_in = arrival day).", "Ask which flight and which hotel in one short question, or take 'the cheapest of both'.",
       "Then propose_trip_booking with both options (a flight only: propose_flight_booking).",
       "For someone else (admin, HR, finance or their manager): resolve them with find_people and pass "
       "for_user_id; pass email_to if the user named an address.", "Read 'say'; ask; stop.", _AFTER),
      required=("search_hotels", "search_flights", "propose_trip_booking", "propose_flight_booking")),
    W("my_flights", M, "My booked flights: 'my flights', 'when is my flight', 'my bookings'.",
      ("list_my_flights",), ("Call list_my_flights.", "Speak the next one or two.")),
]
