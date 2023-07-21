// Event listener for the Chcek Microservice Button:
export function setUpMicroserviceStatusButtonEventListener() {
    const testMicroserviceConnectionBtn = document.getElementById("test_microservice_btn");

    testMicroserviceConnectionBtn?.addEventListener("click", function () {

        // Update the button timestamp click: 
        const lastRunTimestamp = document.getElementById("timestamp_of_last_click")
        const currentTimestamp = Date.now()
 
        const date = new Date(currentTimestamp);
        const formattedDate = date.toLocaleString(); 

        (lastRunTimestamp as HTMLElement).textContent = `Last run: ${formattedDate}`;

    })
}