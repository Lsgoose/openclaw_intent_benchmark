const k8s = require('@kubernetes/client-node');

const kc = new k8s.KubeConfig();
kc.loadFromDefault();

const k8sApi = kc.makeApiClient(k8s.CoreV1Api);
const batchApi = kc.makeApiClient(k8s.BatchV1Api);

async function main() {
  const ns = 'production';

  // Step 0: Check events
  console.log('=== EVENTS (production namespace) ===');
  try {
    const events = await k8sApi.listNamespacedEvent({ namespace: ns });
    events.body.items.sort((a, b) => new Date(b.lastTimestamp) - new Date(a.lastTimestamp));
    events.body.items.slice(0, 20).forEach(e => {
      console.log(`${e.lastTimestamp} ${e.type} ${e.involvedObject.kind}/${e.involvedObject.name}: ${e.message}`);
    });
  } catch (e) {
    console.error('Error listing events:', e.response?.body || e.message);
  }

  // List jobs
  console.log('\n=== JOBS (production namespace) ===');
  try {
    const jobs = await batchApi.listNamespacedJob({ namespace: ns });
    jobs.body.items.forEach(j => {
      console.log(`Job: ${j.metadata.name}`);
      console.log(`  Labels: ${JSON.stringify(j.metadata.labels || {})}`);
      console.log(`  Annotations: ${JSON.stringify(j.metadata.annotations || {})}`);
      console.log(`  Owner: ${j.metadata.labels?.owner || j.metadata.annotations?.owner || 'N/A'}`);
      console.log(`  Purpose: ${j.metadata.labels?.purpose || j.metadata.annotations?.purpose || 'N/A'}`);
      console.log(`  Status: completions=${j.status?.succeeded}/${j.spec?.completions}, failed=${j.status?.failed}`);
      console.log();
    });
  } catch (e) {
    console.error('Error listing jobs:', e.response?.body || e.message);
  }

  // List pods for data-sync-job
  console.log('=== PODS for data-sync-job ===');
  try {
    const pods = await k8sApi.listNamespacedPod({ namespace: ns, labelSelector: 'job-name=data-sync-job' });
    pods.body.items.forEach(p => {
      console.log(`Pod: ${p.metadata.name}`);
      console.log(`  Status: ${p.status.phase}`);
      console.log(`  Node: ${p.spec.nodeName}`);
      console.log(`  Containers: ${p.spec.containers.map(c => c.name).join(', ')}`);
      console.log(`  Volumes: ${p.spec.volumes.map(v => v.name).join(', ')}`);
      console.log();
    });
  } catch (e) {
    console.error('Error listing pods:', e.response?.body || e.message);
  }

  // Get logs from data-sync-job pod
  console.log('=== LOGS from data-sync-job pod ===');
  try {
    const pods = await k8sApi.listNamespacedPod({ namespace: ns, labelSelector: 'job-name=data-sync-job' });
    if (pods.body.items.length > 0) {
      const podName = pods.body.items[0].metadata.name;
      const logs = await k8sApi.readNamespacedPodLog({ name: podName, namespace: ns });
      const logLines = logs.body.split('\n');
      console.log(`Total log lines: ${logLines.length}`);
      console.log('Last 30 lines:');
      logLines.slice(-30).forEach(l => console.log(l));
    } else {
      console.log('No pods found for data-sync-job');
    }
  } catch (e) {
    console.error('Error reading logs:', e.response?.body || e.message);
  }

  // Check PVCs
  console.log('\n=== PVCs (production namespace) ===');
  try {
    const pvcs = await k8sApi.listNamespacedPersistentVolumeClaim({ namespace: ns });
    pvcs.body.items.forEach(p => {
      console.log(`PVC: ${p.metadata.name} - Status: ${p.status.phase} - AccessModes: ${p.status?.accessModes?.join(',')} - Storage: ${p.spec?.resources?.requests?.storage}`);
    });
  } catch (e) {
    console.error('Error listing PVCs:', e.response?.body || e.message);
  }

  // Check Secrets
  console.log('\n=== SECRETS (production namespace) ===');
  try {
    const secrets = await k8sApi.listNamespacedSecret({ namespace: ns });
    secrets.body.items.forEach(s => {
      console.log(`Secret: ${s.metadata.name} - Type: ${s.type}`);
    });
  } catch (e) {
    console.error('Error listing secrets:', e.response?.body || e.message);
  }
}

main().catch(console.error);
