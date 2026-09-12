from rest_framework import serializers

class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200)
    finish = serializers.CharField(max_length=200)

class FuelStopSerializer(serializers.Serializer):
    station_id = serializers.IntegerField()
    name = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    price_per_gallon = serializers.FloatField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    route_mile = serializers.FloatField()
    miles_from_previous_stop = serializers.FloatField()
    gallons_purchased = serializers.FloatField()
    fuel_cost = serializers.FloatField()

class RouteResponseSerializer(serializers.Serializer):
    start = serializers.CharField()
    finish = serializers.CharField()
    total_distance_miles = serializers.FloatField()
    total_fuel_consumed_gallons = serializers.FloatField()
    total_fuel_cost = serializers.FloatField()
    fuel_stops = FuelStopSerializer(many=True)
    route = serializers.JSONField()
    assumptions = serializers.JSONField()
