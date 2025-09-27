# TCP-like Transport Protocol

A reliable, ordered transport protocol implementation featuring congestion control, flow control, and efficient loss recovery mechanisms.

## Features

- **Reliable Data Delivery**: Guarantees all data arrives without loss or corruption
- **In-Order Processing**: Maintains sequence number ordering for application data
- **Congestion Control**: TCP Reno-style algorithm with slow start, congestion avoidance, and fast recovery
- **Selective Acknowledgments**: Efficient ACK mechanism reduces unnecessary retransmissions
- **Fast Retransmit**: Quick loss detection and recovery without waiting for timeouts
- **Adaptive Timeouts**: Dynamic RTO calculation based on network conditions

## Requirements

- Python 3.7+
- Standard library only (no external dependencies)

## Usage

### Running as Receiver

Start a receiver that listens for incoming data:

```bash
python transport.py receiver --ip 127.0.0.1 --port 8000
```

### Running as Sender

Send a file to a running receiver:

```bash
python transport.py sender --ip 127.0.0.1 --port 8000 --sendfile data.txt
```

### Command Line Options

#### Common Options
- `--ip`: IP address to bind (receiver) or connect to (sender)
- `--port`: Port number to use
- `--simloss`: Simulate packet loss (0.0-1.0, default: 0.0)

#### Sender-Specific Options
- `--sendfile`: File containing data to transmit (required for sender)
- `--recv_window`: Receiver window size in bytes (default: 15MB)

### Example Usage

```bash
# Terminal 1: Start receiver
python transport.py receiver --ip 0.0.0.0 --port 9000

# Terminal 2: Send a file with 5% packet loss simulation
python transport.py sender --ip 127.0.0.1 --port 9000 --sendfile document.txt --simloss 0.05
```

## Protocol Details

### Packet Format

All packets use JSON encoding:

**Data Packet:**
```json
{
  "type": "data",
  "seq": [start_seq, end_seq],
  "id": packet_id,
  "payload": "data_string"
}
```

**ACK Packet:**
```json
{
  "type": "ack",
  "sacks": [[start1, end1], [start2, end2], ...],
  "id": packet_id
}
```

**FIN Packet:**
```json
{
  "type": "fin"
}
```

### Configuration Parameters

- **Payload Size**: 1200 bytes maximum per packet
- **Packet Size**: 1500 bytes maximum including headers
- **Initial Congestion Window**: 1 packet
- **Initial Slow Start Threshold**: 64KB
- **RTT Estimation**: α = 0.125, β = 0.25
- **RTO Multiplier**: 4 (EstimatedRTT + 4×DevRTT)

## Implementation Details

### Congestion Control Algorithm

The implementation follows TCP Reno congestion control:

1. **Slow Start**: Exponential window growth until reaching ssthresh
2. **Congestion Avoidance**: Linear window growth in steady state
3. **Fast Recovery**: Maintains higher throughput during loss events

### Loss Detection

- **Duplicate ACKs**: Fast retransmit after 3 duplicate ACKs
- **Timeout**: RTO-based retransmission with exponential backoff
- **SACK**: Selective acknowledgments for efficient recovery

### Buffer Management

- **Receive Buffer**: Stores out-of-order packets until they can be delivered
- **Send Buffer**: Tracks in-flight packets for retransmission
- **Memory Efficient**: Automatic cleanup of acknowledged data

## Testing

### Basic Functionality Test

```bash
# Create test file
echo "Hello, World!" > test.txt

# Start receiver
python transport.py receiver --ip 127.0.0.1 --port 8001 &

# Send file
python transport.py sender --ip 127.0.0.1 --port 8001 --sendfile test.txt

# Verify output
```

### Performance Testing

```bash
# Create large test file
dd if=/dev/zero of=large_file.dat bs=1M count=10

# Test with different loss rates
for loss in 0.0 0.01 0.05 0.1; do
    echo "Testing with $loss packet loss"
    python transport.py sender --ip 127.0.0.1 --port 8002 --sendfile large_file.dat --simloss $loss
done
```

## Troubleshooting

### Common Issue

**Port Already in Use:**
- Try a different port number
- Wait for previous connections to time out
- Use `netstat -an | grep <port>` to check port status

### Debug Output

The implementation includes verbose debug output:

```
send seq: (0, 1200)    ,id: 0
receive seq: [(0, 1200)]    ,id: 0
in slow start
1 new acks
before: ssthresh: 65536    cwnd: 1500
after: ssthresh: 65536    cwnd: 3000
```

### Logging

Enable detailed logging by modifying the print statements in the code, or redirect output:

```bash
python transport.py sender --ip 127.0.0.1 --port 8000 --sendfile data.txt 2> debug.log
```
