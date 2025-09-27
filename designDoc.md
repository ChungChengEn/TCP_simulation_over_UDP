# TCP-like Transport Protocol - Design Document

## Overview

This document describes the design and implementation of a reliable, ordered transport protocol similar to TCP. The protocol implements key TCP features including reliable data delivery, flow control, congestion control, and fast recovery mechanisms.

## Architecture

### Core Components

1. **Receiver Class**: Handles incoming data packets, manages receive buffer, generates ACKs
2. **Sender Class**: Manages data transmission, implements congestion control, handles retransmissions

### Protocol Features

- **Reliable Data Delivery**: Ensures all data is delivered without loss or corruption
- **In-Order Delivery**: Maintains sequence number ordering at the application layer
- **Flow Control**: Respects receiver window size to prevent buffer overflow
- **Congestion Control**: Implements TCP Reno-style congestion control
- **Fast Retransmit/Fast Recovery**: Handles packet loss efficiently

## Detailed Design

### Receiver Implementation

#### Data Structures
- `nextseqnum`: Next expected sequence number for in-order delivery
- `acks`: List of acknowledged sequence ranges
- `receive_buffer`: Out-of-order packet storage

#### Key Algorithms

**Packet Processing Flow:**
1. Check if packet is already acknowledged
2. Determine if packet can be delivered immediately (in-order)
3. Combine adjacent ranges in receive buffer
4. Update acknowledgment ranges
5. Deliver data to application if possible

**ACK Generation:**
- ACKs contain all successfully received sequence ranges
- Selective ACK (SACK) style acknowledgments
- Cumulative ACK for in-order delivery

### Sender Implementation

#### Data Structures
- `base`: Oldest unacknowledged sequence number
- `nextseqnum`: Next sequence number to send
- `cwnd`: Congestion window size
- `ssthresh`: Slow start threshold
- `rto`: Retransmission timeout value

#### Congestion Control States

**1. Slow Start**
- Initial state and after timeout
- Exponential window growth: `cwnd += packet_size` per ACK
- Transition to Congestion Avoidance when `cwnd >= ssthresh`

**2. Congestion Avoidance**
- Linear window growth: `cwnd += (packet_size²)/cwnd` per ACK
- Maintains steady state operation

**3. Fast Recovery**
- Triggered by 3 duplicate ACKs
- Maintains higher throughput during loss recovery
- Sets `cwnd = ssthresh + 3*packet_size`

#### Loss Detection

**Timeout-based Detection:**
- RTO calculation using exponential weighted moving average
- `EstimatedRTT = 0.875*EstimatedRTT + 0.125*SampleRTT`
- `DevRTT = 0.75*DevRTT + 0.25*|SampleRTT - EstimatedRTT|`
- `RTO = EstimatedRTT + 4*DevRTT`

**Fast Retransmit:**
- Triggered by 3 consecutive duplicate ACKs
- Immediate retransmission without waiting for timeout
- Enters Fast Recovery state

### Protocol Flow

#### Connection Establishment
- Simplified compared to TCP (no three-way handshake)
- Sender begins transmission immediately

#### Data Transmission
1. Sender checks congestion window and receiver window
2. Transmits packets within window limits
3. Starts retransmission timer for each packet
4. Waits for ACKs or timeout

#### ACK Processing
1. Update RTT measurements
2. Remove acknowledged packets from flight
3. Detect duplicate ACKs and trigger fast retransmit
4. Update congestion control state
5. Adjust congestion window based on current state

#### Connection Termination
- Sender transmits FIN packet when all data is sent
- Receiver processes remaining buffered data
- Connection resources are cleaned up

## Performance Optimizations

### Efficiency Measures
- Selective acknowledgments reduce unnecessary retransmissions
- Fast retransmit minimizes loss recovery time
- Congestion control prevents network overload
- Efficient buffer management reduces memory usage

### Scalability Considerations
- O(n) complexity for packet processing operations
- Memory usage scales with out-of-order packet count
- Timeout handling uses efficient data structures

## Error Handling

### Packet Loss
- Timeout-based retransmission as fallback
- Fast retransmit for early loss detection
- Congestion window adjustment to prevent further loss

### Network Congestion
- Multiplicative decrease on loss detection
- Additive increase during stable operation
- Slow start after severe congestion (timeout)

### Data Integrity
- JSON packet format with type checking
- Sequence number validation
- Payload size limits

## Protocol Limitations

### Differences from TCP
- No connection establishment handshake
- Simplified state machine
- No advanced features like window scaling
- UDP-based implementation (no built-in reliability)


## Testing Considerations

### Unit Tests
- Receiver packet processing with various orderings
- Sender congestion control state transitions
- RTT estimation accuracy
- Buffer management edge cases

### Integration Tests
- End-to-end data transfer correctness
- Performance under various loss rates
- Congestion control behavior validation
- Timeout and recovery mechanisms

### Performance Tests
- Throughput measurement across different network conditions
- Latency analysis under various loads
- Memory usage profiling
- Scalability testing with large transfers

## Future Enhancements

### Potential Improvements
- Connection establishment protocol
- Advanced congestion control algorithms (BBR, CUBIC)
- Improved error detection and correction
- Multi-threading support
- Protocol security enhancements
- Dynamic timeout adjustment algorithms