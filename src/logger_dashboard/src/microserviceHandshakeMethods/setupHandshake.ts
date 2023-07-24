// Event listener for the Chcek Microservice Button:
async function getServiceStatus(url: string): Promise<any> {
    const response = await fetch(url, {
        method: "GET",
        credentials: "include"
    })

    try {
        if (!response.ok) {
            throw new Error(`Error in HTTP request to microservice endpoint ${response.status} - ${response.statusText}`)
        } else {
            const statusData = await response.json()
            return statusData
        }
    } catch (err) {
        const typedError = err as Error
        throw new Error(`Error while fetching microservice status endpoint data ${typedError.message}`)
    }
}

export function setUpMicroserviceStatusButtonEventListener() {
    const testMicroserviceConnectionBtn = document.getElementById("test_microservice_btn");
    
    // Extracting all of the urls from the input components: 
    const articleSchedulerUrl = (<HTMLInputElement>document.getElementById("article_scheduler_url")).value
    const articleIngestorUrl = (<HTMLInputElement>document.getElementById("article_ingestor_service_url")).value
    const snowflakeServiceUrl = (<HTMLInputElement>document.getElementById("snowflake_service_url")).value
    const storageBucketUrl = (<HTMLInputElement>document.getElementById("storage_bucket_ingestor_service_url")).value

    testMicroserviceConnectionBtn?.addEventListener("click", async function () {

        // Update the button timestamp click: 
        const lastRunTimestamp = document.getElementById("timestamp_of_last_click")
        const currentTimestamp = Date.now()
 
        const date = new Date(currentTimestamp);
        const formattedDate = date.toLocaleString();
        
        (lastRunTimestamp as HTMLElement).textContent = `Last run: ${formattedDate}`;

        // Make HTTP requests to all of the microservices:
        const microserviceUrls: string[] = [
            articleSchedulerUrl, 
            articleIngestorUrl, 
            snowflakeServiceUrl,
            storageBucketUrl
        ]

        // We assume that the ids in the status components are the same as the `microservice_name` field in the status response: 
        // Getting the parent div container of all of the status components: 
        const statusGrid = (<HTMLElement>document.getElementById("microservice_status_containers"))
        const remainingStatusComponents = Array.from(statusGrid.querySelectorAll("div"))

        for (var i = 0; i < microserviceUrls.length; i++) {
            try {
                const microserviceResponse = await getServiceStatus(microserviceUrls[i])
                // Trying to get a specific div component with the id name of the microservice:
                const microserviceComponent = <HTMLDivElement>document.getElementById(microserviceResponse.microservice_name) 
                
                if (microserviceComponent) {
                    microserviceComponent.classList.remove("border-gray-300", "border-red-300", "border-green-300")

                    if (microserviceResponse.status == 200) {
                        microserviceComponent.style.borderColor = 'green';
                        microserviceComponent.classList.add("border-green-300")
                        console.log(`Added Green Component to ${microserviceComponent}`)
                    } else {
                        microserviceComponent.style.borderColor = 'red';
                        microserviceComponent.classList.add("border-red-300")
                        console.log(`Added Green Component to ${microserviceComponent}`)
                    }
                    
                    // Adding the JSON request content to each of the microservice components:
                    const existingJSONComponent= <HTMLPreElement>microserviceComponent.querySelector("pre")
                    if (existingJSONComponent) {
                        microserviceComponent.removeChild(existingJSONComponent)
                    }

                    const jsonString = JSON.stringify(microserviceResponse, null, 2)
                    const jsonElement = document.createElement("pre");
                    jsonElement.textContent = jsonString;
                    jsonElement.classList.add("w-full", "h-full", "overflow-auto", "bg-gray-100", "m-4", "max-h-[200px]", "flex-1")
                    microserviceComponent.appendChild(jsonElement);
                
                const index = remainingStatusComponents.indexOf(microserviceComponent)
                if (index !== -1) {
                    remainingStatusComponents.splice(index, 1)
                }
                // This grid component has been set so now we remove that component from the statusGrid: 
                //const divToRemove = (<HTMLElement>statusGrid.querySelector(`#${microserviceResponse.microservice_name}`))
                //statusGrid.removeChild(divToRemove)
                }
            
            } catch (err) {
                console.error(err)
            }
        }

        // Setting all of the remaining components to 
         remainingStatusComponents.forEach((microserviceComponent) => {
            microserviceComponent.style.borderColor = 'red';
            microserviceComponent.classList.add("border-red-300");
            console.log(`Added Red Component to ${microserviceComponent}`);
        });
        
   })
}