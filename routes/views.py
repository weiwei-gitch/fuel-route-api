from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .serializers import RouteRequestSerializer
from .services.routing import geocode,get_route,RoutingError
from .services.fuel_data import load_fuel_data
from .services.fuel_optimizer import candidates_on_route,optimize_stops

class HealthCheckView(APIView):
    def get(self, request, *args, **kwargs): return Response({'status':'ok'})

class RoutePlanView(APIView):
    def post(self, request, *args, **kwargs):
        serializer=RouteRequestSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        start_text=serializer.validated_data['start']; finish_text=serializer.validated_data['finish']
        try:
            start=geocode(start_text); finish=geocode(finish_text)
            route=get_route(start,finish)
            stations=load_fuel_data()
            candidates=candidates_on_route(route['geojson'],stations)
            stops,consumed,cost=optimize_stops(route['distance_miles'],candidates)
        except (RoutingError,FileNotFoundError,ValueError) as exc:
            return Response({'error':str(exc)},status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response({'start':start['label'],'finish':finish['label'],'total_distance_miles':round(route['distance_miles'],2),'total_fuel_consumed_gallons':round(consumed,2),'total_fuel_cost':cost,'fuel_stops':stops,'route':route['geojson'],'assumptions':{'vehicle_range_miles':500,'vehicle_mpg':10,'starting_tank':'full','starting_fuel_cost_included':False,'route_corridor_miles':15,'station_coordinates':'US Census Gazetteer city/place representative coordinates'}})
