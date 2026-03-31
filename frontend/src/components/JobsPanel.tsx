import { JobLog, JobOutput, JobSummary } from '../types'

type Props = {
  jobs: JobSummary[]
  selectedJobId: string | null
  onSelectJob: (id: string) => void
  onCancelJob: (id: string) => void
  logs: JobLog[]
  outputs: JobOutput[]
}

export default function JobsPanel({ jobs, selectedJobId, onSelectJob, onCancelJob, logs, outputs }: Props) {
  const selectedJob = jobs.find((job) => job.id === selectedJobId) ?? null
  const canCancel = selectedJob ? !['completed', 'failed', 'canceled'].includes(selectedJob.status) : false

  return (
    <div className="jobs-layout">
      <section className="card">
        <h3>Jobs</h3>
        <div className="inline-row">
          <button type="button" disabled={!selectedJobId || !canCancel} onClick={() => selectedJobId && onCancelJob(selectedJobId)}>
            Cancel Selected Job
          </button>
        </div>
        <div className="jobs-list">
          {jobs.map((job) => (
            <button
              type="button"
              key={job.id}
              className={`job-row ${selectedJobId === job.id ? 'selected' : ''}`}
              onClick={() => onSelectJob(job.id)}
            >
              <strong>{job.id}</strong>
              <span>{job.status}</span>
              <span>{Math.round((job.progress ?? 0) * 100)}%</span>
            </button>
          ))}
          {jobs.length === 0 && <p>No jobs yet.</p>}
        </div>
      </section>

      <section className="card">
        <h3>Logs</h3>
        <div className="log-list">
          {logs.map((log) => (
            <div key={log.id} className={`log-entry level-${log.level.toLowerCase()}`}>
              <code>{log.timestamp}</code>
              <strong>{log.level}</strong>
              <span>{log.message}</span>
            </div>
          ))}
          {logs.length === 0 && <p>No logs available.</p>}
        </div>
      </section>

      <section className="card">
        <h3>Outputs</h3>
        <div className="output-list">
          {outputs.map((output) => (
            <div key={output.id} className="output-entry">
              <strong>{output.output_type}</strong>
              <code>{output.path}</code>
            </div>
          ))}
          {outputs.length === 0 && <p>No outputs catalogued yet.</p>}
        </div>
      </section>
    </div>
  )
}
