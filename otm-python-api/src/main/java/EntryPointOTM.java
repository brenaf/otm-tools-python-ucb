import com.google.gson.Gson;
import py4j.GatewayServer;
import java.util.*;
import output.*;


public class EntryPointOTM {

    public ExposedAPI api;
    private Gson gson;

    public EntryPointOTM() {
        api = new ExposedAPI();
        gson = new Gson();
    }

    public void initRequests(float sampleDt) {
    /*
        Request data for LinkFlow before running simulation. Possible requests:
        request_lanegroups, request_links_veh, request_links_veh,
        request_links_flow, request_links_flow, request_lanegroup_flw,
        request_lanegroup_veh, request_path_travel_time,
        request_path_travel_time,request_subnetwork_vht,
        request_vehicle_events, request_vehicle_events, request_vehicle_class,
        request_vehicle_travel_time, request_actuator, request_actuator,
        request_controller, request_controller
    */
        api.request_links_veh(api.get_link_ids(), sampleDt);
        api.request_links_flow(api.get_link_ids(), sampleDt);
    }

    public String generateLinkVeh() {
        HashMap<Long, List<Double>> linkVehs = new HashMap<Long, List<Double>>();
        for (AbstractOutput output: api.get_output_data()) {
            if (output instanceof LinkVehicles) {
                LinkVehicles outputVeh = (LinkVehicles) output;
                for (Long linkId : api.get_link_ids()) {
                    linkVehs.put(linkId, outputVeh.linkprofiles.get(linkId).profile.values);
                }
            }
        }
        return gson.toJson(linkVehs);
    }

    public String generateLinkFlow() {
        HashMap<Long, List<Double>> linkFlows = new HashMap<Long, List<Double>>();
        for (AbstractOutput output: api.get_output_data()) {
            if (output instanceof LinkFlow) {
                LinkFlow outputFlow = (LinkFlow) output;
                for (Long linkId : api.get_link_ids()) {
                    linkFlows.put(linkId, outputFlow.get_flow_for_link_in_vph(linkId));
                }
            }
        }
        return gson.toJson(linkFlows);
    }

    public static void main(String[] args) {
        EntryPointOTM app = new EntryPointOTM();
        GatewayServer server = new GatewayServer(app);
        server.start();
    }
}
