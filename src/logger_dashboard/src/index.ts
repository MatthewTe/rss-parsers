import './style.css';
import { Message } from "paho-mqtt";
import { Grid, GridApi, GridOptions, ModuleRegistry } from "@ag-grid-community/core";
import { ClientSideRowModelModule } from '@ag-grid-community/client-side-row-model';
import { client } from "./mqtt_client";

import { setUpMicroserviceStatusButtonEventListener } from './microservice_status_check';

ModuleRegistry.registerModules([ClientSideRowModelModule])

interface columnDefinition {
    field: string
}

interface rowDefinition {
    Source: string, 
    Timestamp: string,
    Message: string,
    Level: string
}

const columns: columnDefinition[] = [
    {field: "Source"},
    {field: "Timestamp"},
    {field: "Message"},
    {field: "Level"}
]

const gridOptions: GridOptions = <GridOptions>{
    columnDefs: columns,
    rowData: [],
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("DOMContentLoaded event fired");
    console.log("Starting to Add Event Listener")
    setUpMicroserviceStatusButtonEventListener();
    console.log("After Adding Event Listener")
   const logStreamDiv:HTMLElement = <HTMLElement>document.querySelector("#log-stream-grid")
    const grid = new Grid(logStreamDiv, gridOptions)
    logStreamDiv.classList.add('ag-theme-alpine-dark');
})


let mainRowData: rowDefinition[] = []

client.onMessageArrived = function (message: Message) {
    
    console.log("Message received:", message.payloadString); 
    var log = JSON.parse(message.payloadString)
    var newRow: rowDefinition[] = [
        {
            Source: log.source,
            Timestamp: log.timestamp,
            Message: log.message,
            Level: log.level
        }
    ]
    mainRowData = mainRowData.concat(newRow)
    gridOptions.api?.setRowData(mainRowData)

}


