package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
)

type Method string

const (
	MethodAuthenticate       Method = "Authenticate"
	MethodRegisterClient     Method = "RegisterClient"
	MethodGetDevicesExtended Method = "GetDevicesExtended"
	MethodActivateScenario   Method = "ActivateScenario"
)

type ReqData struct {
	Method Method         `json:"Method"`
	Params map[string]any `json:"Params"`
}

var activeScenario = map[int]int{
	545002: 1,
}

func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {

		reqJson := r.URL.Query().Get("req")

		reqData := &ReqData{}
		err := json.Unmarshal([]byte(reqJson), reqData)
		if err != nil {
			WriteError(w, http.StatusBadRequest, "Invalid JSON request")
			return
		}

		fmt.Printf("Received request with method: %s\n", reqData.Method)

		switch reqData.Method {
		case MethodAuthenticate:
			WriteJson(w, map[string]any{
				"Token": "e255f93b-467c-4248-9315-879fa727d82d",
				"TTL":   3600,
			})
		case MethodRegisterClient:
			WriteJson(w, map[string]any{
				"Token": "e255f93b-467c-4248-9315-879fa727d82d",
				"TTL":   3600,
			})

		case MethodGetDevicesExtended:
			WriteJson(w, map[string]any{
				"Devices": []map[string]any{
					{
						"DeviceId":       545002,
						"ActiveScenario": activeScenario[545002],
						"Name":           "BLUEBERR 3",
						"Scenarios": []map[string]any{
							{
								"ScenarioId": 0,
								"Name":       "ARM",
							},
							{
								"ScenarioId": 1,
								"Name":       "DISARM",
							},
							{
								"ScenarioId": 2,
								"Name":       "STAY",
							},
						},
					},
				},
			})
		case MethodActivateScenario:
			scenarioIdStr := reqData.Params["ScenarioId"].(string)
			deviceIdStr := reqData.Params["DeviceId"].(string)

			scenarioId, _ := strconv.Atoi(scenarioIdStr)
			deviceId, _ := strconv.Atoi(deviceIdStr)

			activeScenario[int(deviceId)] = int(scenarioId)
			WriteJson(w, map[string]any{})

		default:
			WriteError(w, http.StatusBadRequest, "Unknown method")
		}
	})

	fmt.Println("Server is running on http://localhost:8080")
	http.ListenAndServe(":8080", mux)
}

func WriteJson(w http.ResponseWriter, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	resData := map[string]any{
		"Status": 0,
		"Data":   data,
	}

	if err := json.NewEncoder(w).Encode(resData); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

func WriteError(w http.ResponseWriter, status int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)

	errorResponse := map[string]string{"error": message}
	if err := json.NewEncoder(w).Encode(errorResponse); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}
