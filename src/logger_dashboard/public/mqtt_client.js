import { Client } from "paho-mqtt";
var wsbroker = 'localhost';
var wsport = 15675;
export const client = new Client(wsbroker, wsport, "/ws", "myclientid_10");
var connectionOptions = {
    timeout: 3,
    keepAliveInterval: 30,
    onSuccess: function () {
        console.log("Broker Connection Success");
        client.subscribe("+/DEBUG", { qos: 1 });
        console.log("Subscribed to all DEBUG Logs");
        client.subscribe("+/INFO", { qos: 1 });
        console.log("Subscribed to all INFO Logs");
        client.subscribe("+/WARNING", { qos: 1 });
        console.log("Subscribed to all WARNING Logs");
        client.subscribe("+/ERROR", { qos: 1 });
        console.log("Subscribed to all ERROR Logs");
    },
    onFailure: function (message) {
        console.log("Error in connecting to message broker: " + message.errorMessage);
    }
};
client.connect(connectionOptions);
