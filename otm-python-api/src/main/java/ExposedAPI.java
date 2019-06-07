import control.sigint.ScheduleItem;
import control.sigint.Stage;
import api.API;

import java.util.*;

public class ExposedAPI extends API {
    // Original API.java in otm-sim has a protected scenario, but
    // modifying the controller through the APIs requires creating
    // a separate API class which have methods that can modify the
    // scenario and is initialized by the PyOTM entry point.

    public void insertActuatorSchedule(Long actuatorId, ScheduleItem schedItem){
        ControllerSignalPretimedInternal masterControl = (ControllerSignalPretimedInternal) 
                        scenario.controllers.values().iterator().next();
        masterControl.assignedSchedules.put(actuatorId, schedItem);
        System.out.printf("Schedule [%s] for Actuator %d inserted\n", schedItem, actuatorId);
    }

    public void insertActuatorSchedule(Integer actuatorId, ArrayList<Double> stageTimings){
        List<Stage> stageList = new ArrayList<>();
        for (int idx = 0; idx < stageTimings.size(); idx++){
            Stage stageItem = new Stage(idx, stageTimings.get(idx).floatValue(),
                        new Long[]{Long.valueOf(idx)});
            stageList.add(stageItem);
        }
        ScheduleItem newSched = new ScheduleItem(0f, 0f, stageList);
        insertActuatorSchedule(Long.valueOf(actuatorId), newSched);
    }

    public String initSignalStages() {
        // Assume that the network only uses a single global controller    
        return String.format("ACTUATORS: %s\nCONTROLLERS: %s",
            scenario.actuators, scenario.controllers);
    };


}