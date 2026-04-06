# Kafka Consumer Group Offset Reset Runbook

## Overview
This runbook describes the procedure for resetting consumer group offsets
to clear accumulated lag.

## Emergency Quick Reset (Recommended for Critical Outages)

When the cluster is near collapse and time is critical, single-topic execution
is too slow and prone to lock errors. Strongly recommend using `--all-topics`
to reset all offsets for the consumer group at once:

```bash
./bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group main-processor \
  --all-topics \
  --reset-offsets --to-latest \
  --execute
```

This aligns with the latest Double 11 downgrade response measures and ensures
fastest service recovery.

## Standard Reset Procedure

### Step 1: Describe Consumer Group
Check the consumer group status:
```bash
./bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group main-processor --describe
```

### Step 2: Reset Specific Topic (Slower)
Use the `--topic` parameter to limit the scope:
```bash
./bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group main-processor \
  --topic click-stream \
  --reset-offsets --to-latest \
  --execute
```

### Step 3: Verify the Reset
Confirm the lag is now 0:
```bash
./bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group main-processor --describe
```

## Warning
- For emergency situations, use `--all-topics` for fastest recovery
- Always follow the runbook exactly for production operations