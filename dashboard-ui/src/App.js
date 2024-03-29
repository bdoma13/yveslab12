import logo from './logo.png';
import './App.css';

import EndpointAudit from './components/EndpointAudit'
import AppStats from './components/AppStats'
import HealthStatus from './components/HealthStatus'

function App() {

    const endpoints = ["ticket_item", "review_item"]

    const rendered_endpoints = endpoints.map((endpoint) => {
        return <EndpointAudit key={endpoint} endpoint={endpoint}/>
    })

    return (
        <div className="App">
            <img src={logo} className="App-logo" alt="logo" height="150px" width="400px"/>
            <div>
                <AppStats/>
                <HealthStatus/>
                <h1>Audit Endpoints</h1>
                {rendered_endpoints}
            </div>
        </div>
    );

}



export default App;
