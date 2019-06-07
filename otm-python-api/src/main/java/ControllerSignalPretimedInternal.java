/**
 * Copyright (c) 2018, Gabriel Gomes
 * All rights reserved.
 * This source code is licensed under the standard 3-clause BSD license found
 * in the LICENSE file in the root directory of this source tree.
 */

import actuator.AbstractActuator;
import actuator.sigint.ActuatorSignal;
import api.events.EventControllerScheduleTransition;
import common.Link;
import common.RoadConnection;
import control.AbstractController;
import control.sigint.ScheduleItem;
import dispatch.AbstractEvent;
import dispatch.Dispatcher;
import dispatch.EventPoke;
import error.OTMErrorLog;
import error.OTMException;
import jaxb.Controller;
import runner.Scenario;
import java.util.Collection;

import com.google.common.collect.ArrayListMultimap;

public class ControllerSignalPretimedInternal extends AbstractController {

    // public List<ScheduleItem> schedule;
    public Integer current_schedule_item_index;
    // Create a multimap of schedules across the actuators present
    public ArrayListMultimap<Long, ScheduleItem> assignedSchedules;
    ///////////////////////////////////////////////////
    // construction
    ///////////////////////////////////////////////////

    public ControllerSignalPretimedInternal(Scenario scenario, Controller jaxb_controller) throws OTMException {
        super(scenario, jaxb_controller);

        // System.out.println("Initial schedule: " + this.schedule);
        // this.schedule = new ArrayList<>();
        this.assignedSchedules = ArrayListMultimap.create();
        // Collections.sort(schedule);

        // for (ScheduleItem item: schedule) {
        //     for (Stage stage : item.stages.queue) {
        //         System.out.printf("%s,%s,%s: %s %s \t %s\n",item.start_time, item.cycle, item.offset,stage.order, stage.duration, stage.phase_ids);
        //     }
        // }

        // Guarantee that all the actuators present have assigned schedules, otherwise
        // remove the actuator and the node will behave as a inactive signal intersection.
        // this.actuators.removeIf(act -> !assignedSchedules.containsKey(act.id));
        // for (Collection<ScheduleItem> sched : assignedSchedules.asMap().values()){
        //     System.out.println(sched);
        //     for (ScheduleItem item : sched) {
        //         System.out.println(item + ": " + item.start_time);
        //     }
        // }

        // System.out.println("Initial actuators: " + actuators);
    }

    ///////////////////////////////////////////////////
    // initialize
    ///////////////////////////////////////////////////

    @Override
    public void validate(OTMErrorLog errorLog) {
        super.validate(errorLog);

        // Enumerate schedule items
        // for (ScheduleItem item : schedule) {
        //     System.out.printf("NEXT SWAP %s - %s \n", item, item.start_time);
        // }

        // for(ScheduleItem item : schedule)
        //     item.validate(errorLog);
    }

    @Override
    public void poke(Dispatcher dispatcher, float timestamp) throws OTMException {
        // System.out.println("POKE: " + timestamp + "\t" + current_schedule_item_index);
        super.poke(dispatcher, timestamp);
    }
    
    @Override
    public void initialize(Scenario scenario,float now) throws OTMException {
        // System.out.println("INITIALIZING");
        this.actuators.values().removeIf(act -> !assignedSchedules.containsKey(act.id));
        // for (RoadConnection rc : scenario.network.road_connections.values()){
        //     System.out.printf("%s - %s\n", rc, rc.external_max_flow_vps);
        // }
        current_schedule_item_index = 0;//get_item_index_for_time(now);

        // not reached first item, set all to dark
        if(current_schedule_item_index == null) {
            for (AbstractActuator actuator: actuators.values()) {
                ((ActuatorSignal) actuator).turn_off(now);
                System.out.println("Turning off: " + actuator);
            }
            // ((ActuatorSignal) actuators.iterator().next()).turn_off(now);
            return;
        }

        // inform output writer
        if(event_listener !=null){
            System.out.println("INFORMING OUTPUT WRITER (SCHEDULE TRANSITION");
            event_listener.write(now, new EventControllerScheduleTransition(now,id,current_schedule_item_index));
        }
    }

    @Override
    public void register_with_dispatcher(Dispatcher dispatcher) {
        // register next schedule item change
        // register_next_poke(dispatcher);
        // System.out.println("REGISTERING INITIAL EVENTS");
        dispatcher.register_event(new EventPoke(dispatcher,2,dispatcher.current_time + dt,this));

    }

    @Override
    public Object get_command_for_actuator_id(Long act_id) {
        // System.out.println("GETTING COMMAND: " + current_schedule_item_index + " FOR ACT: " + act_id);
        for (AbstractActuator actuator : actuators.values()){
            if ((actuator.id == act_id) && (assignedSchedules.keySet().contains(actuator.id))){
                return assignedSchedules.get(actuator.id).get(0);
            }
        }
        // Return null by default (this will set all phases to dark)
        return null;        
        // return schedule.get(current_schedule_item_index);
    }

    ///////////////////////////////////////////////////
    // update
    ///////////////////////////////////////////////////

    @Override
    public void update_controller(Dispatcher dispatcher, float timestamp) throws OTMException {
        // System.out.println("UPDATE: " + timestamp + "\t" + current_schedule_item_index);
        // advance current schedule item index

        // for (RoadConnection rc : dispatcher.scenario.network.road_connections.values()){
        //     System.out.printf("%s - %s\n", rc, rc.external_max_flow_vps);
        // }

        // if (timestamp < 1000f)
        //     ((ActuatorSignal) actuators.iterator().next()).turn_off(timestamp);
        // if(advance_schedule_item_index(dispatcher.current_time)) {
        //     // send current item to actuator
        //     System.out.println("ADVANCE TRIGGERED");
        //     get_signal().process_controller_command(get_command_for_actuator_id(null),dispatcher,timestamp);
        //     // inform output writer
        //     if(event_listener !=null)
        //         event_listener.write(timestamp, new EventControllerScheduleTransition(timestamp,id,current_schedule_item_index));
        // }

        /** NOTE: For the max pressure algorithm 
        Weights are computed per phase, where: (between all upstream -> downstream mapping)
            phase-weight = (in-link queue length) - sum_{upstream of out-link}(out-link queue length * out-link drain rate)
        Signal pressure is computed by:
            = sum_{phase road connections}(phase saturation rate * phase weight)

        **/



        // for (AbstractSensor sensor : sensor_by_usage.values()) {
        //     FixedSensor the_sensor = (FixedSensor) sensor;
        //     System.out.printf("%d:%.1f, ", the_sensor.id, the_sensor.get_flow_vph());
        // }
        // System.out.println("");

        // for (AbstractActuator actuator: actuators){ 
        //     System.out.printf("ACTUATOR STATE: %d ::: ", actuator.id);
        //     for (SignalPhase phase : ((ActuatorSignal) actuator).signal_phases.values()){
        //         System.out.printf("%s - %s \t", phase.id, phase.bulbcolor);   
        //     }
        //     System.out.println("");
        // }

        // for (SignalPhase phase : ((ActuatorSignal) actuators.iterator().next()).signal_phases.values()) {
        //     System.out.printf("%s - %s \t", phase.id, phase.bulbcolor);
        // }
        // System.out.println("");

        // for (AbstractLaneGroup lg: dispatcher.scenario.network.get_lanegroups()) {
        //     LaneGroup pqlg = (LaneGroup) lg;
        //     System.out.printf("%d:%d, ", pqlg.link.getId(), pqlg.waiting_queue.num_vehicles());
        // }
        // System.out.println("");


    }

    ///////////////////////////////////////////////////
    // getters
    ///////////////////////////////////////////////////

    public ActuatorSignal get_signal(){
        System.out.println("FETCHING SIGNAL ACTUATOR");
        return (ActuatorSignal) actuators.values().iterator().next();
    }

    // public Integer get_item_index_for_time(float time){
    //     if(schedule.isEmpty())
    //         return null;
    //     int s = 0;
    //     if(time<schedule.get(0).start_time)
    //         return null;
    //     for(int e=1;e<schedule.size();e++){
    //         if(time < schedule.get(e).start_time)
    //             break;
    //         s = e;
    //     }
    //     return s;
    // }

    ///////////////////////////////////////////////////
    // private
    ///////////////////////////////////////////////////


}
