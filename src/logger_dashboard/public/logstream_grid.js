import { Grid } from "@ag-grid-community/core";
import { client } from "./mqtt_client";
const columns = [
    { field: "Source" },
    { field: "Timestamp" },
    { field: "Message" },
    { field: "Level" }
];
const gridOptions = {
    columnDefs: columns,
    rowData: [],
};
document.addEventListener("DOMContentLoaded", () => {
    const logStreamDiv = document.querySelector("#log-stream-grid");
    new Grid(logStreamDiv, gridOptions);
});
let mainRowData = [];
client.onMessageArrived = function (message) {
    var _a;
    var log = JSON.parse(message.payloadString);
    var newRow = [
        {
            Source: log.source,
            Timestamp: log.timestamp,
            Message: log.message,
            Level: log.levl
        }
    ];
    mainRowData = mainRowData.concat(newRow);
    (_a = gridOptions.api) === null || _a === void 0 ? void 0 : _a.setRowData(mainRowData);
};
