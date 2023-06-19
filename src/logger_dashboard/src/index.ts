import { Message } from "paho-mqtt";
import { Grid, GridApi, GridOptions, ModuleRegistry } from "@ag-grid-community/core";
import { ClientSideRowModelModule } from '@ag-grid-community/client-side-row-model';
import { client } from "./mqtt_client";

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
    const logStreamDiv:HTMLElement = <HTMLElement>document.querySelector("#log-stream-grid")
    new Grid(logStreamDiv, gridOptions)
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


