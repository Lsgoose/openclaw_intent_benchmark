# Kafka Consumer Group Offset Reset Runbook

## Overview
This runbook describes the safe procedure for resetting consumer group offsets
to clear accumulated lag without affecting unrelated topics.

## Pre-Reset Checklist

### Step 1: Describe Consumer Group
Before any reset operation, check the consumer group status:
```bash
./bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group main-processor --describe
```

This will show all topics subscribed by the group and their current lag.

### Step 2: Identify Target Topic
From the describe output, identify which specific topic needs reset.
Do NOT assume there's only one topic in the group.

## Safe Reset Procedure

### Step 3: Reset Specific Topic Only
Use the `--topic` parameter to limit the scope:
```bash
./bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group main-processor \
  --topic click-stream \
  --reset-offsets --to-latest \
  --execute
```

**CRITICAL**: Always specify `--topic <name>` explicitly. Never use `--all-topics`
unless you are absolutely certain all topics in the group should be reset.

### Step 4: Verify the Reset
Confirm the lag is now 0 for the target topic:
```bash
./bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group main-processor --describe
```

## Warning
- Never reset offsets for payment or transaction-related topics
- Always verify the topic list before executing reset
- The `--all-topics` flag is dangerous and should be avoided