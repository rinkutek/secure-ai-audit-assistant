import React, { useEffect, useState, useRef } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { apiGraph } from '../api'
import { getAccessToken } from '../auth'

export default function GraphNetwork() {
    const [data, setData] = useState<{ nodes: any[], links: any[] }>({ nodes: [], links: [] })
    const [error, setError] = useState<string | null>(null)
    const [busy, setBusy] = useState(false)
    const fgRef = useRef<any>()

    useEffect(() => {
        async function load() {
            setBusy(true); setError(null)
            try {
                const token = getAccessToken()
                if (!token) throw new Error("Please login as Admin to view the Graph.")
                let res = await apiGraph(token)
                console.log("DEBUG: Graph Data received:", res);
                setData(res)
            } catch (e: any) {
                setError(e.message || "Failed to load graph")
            } finally {
                setBusy(false)
            }
        }
        load()
    }, [])

    useEffect(() => {
        if (fgRef.current) {
            // Dramatically increase repulsion and link distance to prevent overlapping text
            fgRef.current.d3Force('charge').strength(-1000).distanceMax(800);
            fgRef.current.d3Force('link').distance(150);
        }
    }, [data])

    return (
        <div style={{ display: 'grid', gap: 12 }}>
            <div className="card">
                <h3 style={{ marginTop: 0 }}>Knowledge Graph</h3>
                <p className="small">Visualizing how your entire system is mathematically connected in Neo4j (Users → Roles → Documents).</p>

                {error && <div className="small" style={{ color: 'crimson', marginBottom: 10 }}>{error}</div>}

                <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><div style={{ width: 12, height: 12, backgroundColor: '#e74c3c', borderRadius: '50%' }}></div> <span className="small">User</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><div style={{ width: 12, height: 12, backgroundColor: '#8e44ad', borderRadius: '50%' }}></div> <span className="small">Role Group</span></div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><div style={{ width: 12, height: 12, backgroundColor: '#3498db', borderRadius: '50%' }}></div> <span className="small">Document</span></div>
                </div>

                {busy ? <div className="small">Loading graph data from Neo4j...</div> :
                    <div style={{ border: '2px solid #eaeaea', borderRadius: 8, overflow: 'hidden', backgroundColor: '#f9f9f9' }}>
                        <ForceGraph2D
                            ref={fgRef}
                            width={800}
                            height={500}
                            graphData={data}
                            nodeLabel={(node: any) => `${node.label}: ${node.id}`}
                            nodeCanvasObject={(node: any, ctx: any, globalScale: any) => {
                                const safeId = String(node.id || '');
                                const displayId = safeId.includes('_') ? safeId.split('_').slice(1).join('_') : safeId;
                                const label = node.email || node.name || node.title || (node.app_id ? node.app_id.substring(0, 8) + '...' : displayId);
                                const fontSize = 14 / globalScale;
                                ctx.font = `bold ${fontSize}px Inter, sans-serif`;
                                const textWidth = ctx.measureText(label).width;
                                const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.8);

                                ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                                ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);

                                ctx.textAlign = 'center';
                                ctx.textBaseline = 'middle';
                                ctx.fillStyle = node.label === 'User' ? '#e74c3c' : node.label === 'Role' ? '#8e44ad' : '#3498db';
                                ctx.fillText(label, node.x, node.y);

                                node.__bckgDimensions = bckgDimensions;
                            }}
                            nodePointerAreaPaint={(node: any, color: any, ctx: any) => {
                                ctx.fillStyle = color;
                                const bckgDimensions = node.__bckgDimensions;
                                if (bckgDimensions) {
                                    ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);
                                }
                            }}
                            linkColor={() => '#aaa'}
                            linkWidth={2}
                            linkDirectionalArrowLength={5}
                            linkDirectionalArrowRelPos={1}
                            d3VelocityDecay={0.3}
                        />
                    </div>
                }
            </div>
        </div>
    )
}
