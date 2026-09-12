from django.test import SimpleTestCase
from routes.services.fuel_optimizer import optimize_stops

class OptimizerTests(SimpleTestCase):
    def test_short_trip_needs_no_paid_stops(self):
        stops, gallons, cost=optimize_stops(400, [], 10, 500)
        self.assertEqual(stops, []); self.assertEqual(gallons,40); self.assertEqual(cost,0)

    def test_no_reachable_station_fails(self):
        with self.assertRaises(ValueError): optimize_stops(900,[{'route_mile':600,'price':3.0}],10,500)
