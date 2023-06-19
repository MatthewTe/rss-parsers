import { Client, ConnectionOptions } from "paho-mqtt";

var wsbroker: string = 'localhost'
var wsport: number = 15675
export const client: Client = new Client(
    wsbroker,
    wsport,
    "/ws",
    "myclientid_10",
)

interface connectionOptions {
    timeout: number,
    keepAliveInterval: number,
    onSuccess: () => void, 
    onFailure: () => void
}

var connectionOptions: ConnectionOptions = {
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

client.connect(connectionOptions)
