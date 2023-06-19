var wsbroker = "localhost";
var wsport = 15675; 
var client = new Paho.MQTT.Client(
    wsbroker,
    wsport,
    "/ws",
    "myclientid_" + parseInt(Math.random() * 100, 10)
);


var options = {
    timeout: 3,
    keepAliveInterval: 30,
    onSuccess: function () {
        console.log("Broker Connection Success")

        client.subscribe("+/DEBUG", {qos: 1})
        console.log("Subscribed to all DEBUG Logs")
        
        client.subscribe("+/INFO", {qos: 1})
        console.log("Subscribed to all INFO Logs")
        
        client.subscribe("+/WARNING", {qos: 1})
        console.log("Subscribed to all WARNING Logs")
        
        client.subscribe("+/ERROR", {qos: 1})
        console.log("Subscribed to all ERROR Logs")
    },
    onFailure: function (message) {
        console.log("Error in connecting to message broker: " + message.errorMessage)
    }
}

client.connect(options)

const columDefs = [
    {field: "Source"},
    {field: "Timestamp"},
    {field: "Message"},
    {field: "Level"},
]

mainRowData = []

const gridOptions = {
    columnDefs: columDefs,
    rowData: [],
    animateRows: true
}

document.addEventListener('DOMContentLoaded', () => {
    const logStreamDiv = document.querySelector("#log-stream-grid")
    new agGrid.Grid(logStreamDiv, gridOptions)
})

client.onMessageArrived = function (message) {

    var log = JSON.parse(message.payloadString)
    var newRow = [
        {
            Source: log.source, 
            Timestamp: log.timestamp, 
            Message: log.message, 
            Level: log.level
        }
    ]
    mainRowData = mainRowData.concat(newRow)
    gridOptions.api.setRowData(mainRowData)
}