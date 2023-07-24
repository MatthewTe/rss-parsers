import './style.css'
import { setUpMicroserviceStatusButtonEventListener } from "./microserviceHandshakeMethods/setupHandshake";

document.addEventListener("DOMContentLoaded", function(){
    console.log("Starting to Add Event Listener")
    setUpMicroserviceStatusButtonEventListener();
    console.log("After Adding Event Listener")
})