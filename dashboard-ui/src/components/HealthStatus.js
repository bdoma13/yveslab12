import React, { useEffect, useState} from 'react'
import '../App.css';

export default function HealthStatus() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [stats, setStats] = useState({});
    const [error, setError] = useState(null)
	const getHealth = () => {
        fetch(`http://acit3855-hosung.westus3.cloudapp.azure.com/health/status`)
            .then(res => res.json())
            .then((result)=>{
				console.log("Received Health")
                setStats(result);
                setIsLoaded(true);
            },(error) =>{
                setError(error)
                setIsLoaded(true);
            })
    };

    useEffect(() => {
		const interval = setInterval(() => getHealth(), 2000); // Update every 2 seconds
		return() => clearInterval(interval);
    }, [getHealth]);
    if (error){
        return (<div className={"error"}>Error found when fetching from API</div>)
    } else if (isLoaded === false){
        return(<div>Loading...</div>)
    } else if (isLoaded === true){
        return(
            <div>
                <h1>Service Status</h1>
                <div className="HealthTable">
                <table className="StatsTable">
                    <tbody>
					    <thead>
                            <tr>
                                <th>Service</th>
                                <th>Status</th>
                            </tr>
						</thead>
						<tr>
							<td>Receiver</td>
							<td>{stats['receiver']}</td>
						</tr>
						<tr>
							<td>storage</td>
							<td>{stats['storage']}</td>
						</tr>
                        <tr>
							<td>Processing</td>
							<td>{stats['processing']}</td>
						</tr>
                        <tr>
							<td>Audit</td>
							<td>{stats['audit_log']}</td>
						</tr>
					</tbody>
                </table>
                </div>
                <h3>Last Updated: {stats['last_updated']}</h3>
            </div>
        )
    }
}
