# Your Name: \u937e\u627f\u6069
# Your ID: B113040003

import argparse
import json
import random
import socket
import time
from typing import Any, Dict, List, Optional, Tuple

# Note: In this starter code, we annotate types where
# appropriate. While it is optional, both in python and for this
# course, we recommend it since it makes programming easier.

# The maximum size of the data contained within one packet
payload_size = 1200
# The maximum size of a packet including all the JSON formatting
packet_size = 1500

class Receiver:
    def __init__(self):
        # TODO: Initialize any variables you want here, like the receive
        # buffer, initial congestion window and initial values for the timeout
        # values
        self.nextseqnum: int = 0
        self.acks: List[Tuple[int,int]] = []
        self.receive_buffer: Dict[Tuple[int,int], str] = {}

    def data_packet(self, seq_range: Tuple[int, int], data: str) -> Tuple[List[Tuple[int, int]], str]:
        '''This function is called whenever a data packet is
        received. `seq_range` is the range of sequence numbers
        received: It contains two numbers: the starting sequence
        number (inclusive) and ending sequence number (exclusive) of
        the data received. `data` is a binary string of length
        `seq_range[1] - seq_range[0]` representing the data.

        It should output the list of sequence number ranges to
        acknowledge and any data that is ready to be sent to the
        application. Note, data must be sent to the application
        _reliably_ and _in order_ of the sequence numbers. This means
        that if bytes in sequence numbers 0-10000 and 11000-15000 have
        been received, only 0-10000 must be sent to the application,
        since if we send the latter bytes, we will not be able to send
        bytes 10000-11000 in order when they arrive. The transport
        layer must hide hide all packet reordering and loss.

        The ultimate behavior of the program should be that the data
        sent by the sender should be stored exactly in the same order
        at the receiver in a file in the same directory. No gaps, no
        reordering. You may assume that our test cases only ever send
        printable ASCII characters (letters, numbers, punctuation,
        newline etc), so that terminal output can be used to debug the
        program.

        '''

        # TODO
        start, end = seq_range
        for ack in self.acks:
            if ack[0] <= start and ack[1] >= end:   # the packet is already acked
                return (self.acks, "")  # return stored acks and an empty string
        
        # if it is a new packet
        ## is it in-order?
        can_be_sent = (self.nextseqnum == start)
        data_sent = ""
        
        ## combined the range if possible
        left_range = None
        right_range = None 
        combined_data = data
        for range in self.receive_buffer.keys():
            if range[0] == end:   right_range = range
            elif range[1] == start:   left_range = range
        if left_range:  
            start = left_range[0]
            combined_data = self.receive_buffer.pop(left_range) + combined_data
        if right_range:
            end = right_range[1]
            combined_data = combined_data + self.receive_buffer.pop(right_range)
        self.receive_buffer[(start,end)] = combined_data
        
        ## update acks, receive_buffer, and nextseqnum
        sorted_ack_range = sorted(self.receive_buffer.keys())
        if can_be_sent:
            self.nextseqnum = end
            data_sent = combined_data
            for range in sorted_ack_range:
                if self.nextseqnum > range[0]:
                    del self.receive_buffer[range] 
                else:   # self.nextseqnum < range[0] : leave the packet in the buffer
                        # no self.nextseqnum == range[0] case: if so, it is in-order and can be sent
                    break
            sorted_ack_range = sorted(self.receive_buffer.keys())
            sorted_ack_range.insert(0, (0, self.nextseqnum))
            self.acks = sorted_ack_range
        else:
            ## can't be sent
            ## self.nextseqnum remains the same
            ## because no sent packets, so no need to modify receive_buffer
            
            ## update acks only
            temp_ack = self.acks.copy()
            for ack in temp_ack:
                if start <= ack[0] and end >= ack[1]:
                    self.acks.remove(ack)
            self.acks.append((start,end))
            self.acks = sorted(self.acks) 
                  
        
        return (self.acks, data_sent)  # Replace this

    def finish(self):
        '''Called when the sender sends the `fin` packet. You don't need to do
        anything in particular here. You can use it to check that all
        data has already been sent to the application at this
        point. If not, there is a bug in the code. A real transport
        stack will deallocate the receive buffer. Note, this may not
        be called if the fin packet from the sender is locked. You can
        read up on "TCP connection termination" to know more about how
        TCP handles this.

        '''

        # TODO
        if self.acks and len(self.acks)==1:
            print(f"acks: {self.acks}")
            print("Successful!")

class Sender:
    def __init__(self, data_len: int):
        '''`data_len` is the length of the data we want to send. A real
        transport will not force the application to pre-commit to the
        length of data, but we are ok with it.

        '''
        # TODO: Initialize any variables you want here, for instance a
        # data structure to keep track of which packets have been
        # sent, acknowledged, detected to be lost or retransmitted
        self.complete = False
        
        self.data_len = data_len 
        self.base = 0
        self.nextseqnum = 0
        
        self.prev_sacks: List[int] = []
        self.sacks: List[Tuple[int,int]] = []
        self.nacks: List[Tuple[int,int]] = []
        
        self.duplicate_count: Dict[Tuple[int,int],int] = {}
        self.retransmit_queue: List[Tuple[int,int]] = []
        self.timeout_queue: List[Tuple[int,int]] = []
        self.record_miss = set()
        
        self.state = 1
        self.SLOW_START = 1
        self.CONGEST_AVOID = 2
        self.FAST_RECOVERY = 3
        
        self.rtt_time: Dict[Tuple[int,int], float] = {}
        self.estimatedRTT = 0
        self.devRTT = 0
        self.rto = 1    # retransmit timeout
        
        self.cwnd = packet_size
        self.ssthresh = 64*1024
        
        self.fast_recovery_packet = None
        self.inflight = 0
        self.MAXCWND = 0
        
        

        
        

    def timeout(self):
        '''Called when the sender times out.'''
        # TODO: In addition to what you did in assignment 1, set cwnd to 1
        # packet
        self.inflight = 0
        self.retransmit_queue.clear()
        self.nacks.sort(key=lambda x: x[0])
        for nack in self.nacks:
            self.timeout_queue.append(nack)
            if nack in self.duplicate_count:    # timeout occur, duplicateACK = 0
                del self.duplicate_count[nack] 
        #self.timeout_queue = self.nacks.copy() 
        
        print("timeout occur")
        print("go to slow start")
        print(f"before: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}\trto: {self.rto}")
        self.state = self.SLOW_START
        self.ssthresh = max(self.cwnd//2, packet_size)
        self.cwnd = 1*packet_size
        self.rto *= 2
        print(f"after: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}\trto: {self.rto}")
        
        for nack in self.nacks:
            if nack in self.rtt_time:   del self.rtt_time[nack]
            
        # for key in self.duplicate_count:
        #     self.timeout_queue.append(key)
        

        #self.duplicate_count.clear()
        
        for miss in self.record_miss:
            self.timeout_queue.append(miss)
        self.record_miss.clear()
            
        self.nacks.clear()
        

    def ack_packet(self, sacks: List[Tuple[int, int]], packet_id: int) -> int:
        '''Called every time we get an acknowledgment. The argument is a list
        of ranges of bytes that have been ACKed. Returns the number of
        payload bytes new that are no longer in flight, either because
        the packet has been acked (measured by the unique ID) or it
        has been assumed to be lost because of dupACKs. Note, this
        number is incremental. For example, if one 100-byte packet is
        ACKed and another 500-byte is assumed lost, we will return
        600, even if 1000s of bytes have been ACKed before this.

        '''

        # TODO
        #debug
        print(f"receive seq: {sacks}\t,id: {packet_id}")
        print(f"self.nacks: {self.nacks}")
        
        off_flight = 0
        ack_receive_time = time.perf_counter()
        #is_new_ack = False
        new_acks: List[Tuple[int,int]] = []
        nacks_index = 0
        first_dupACK = None
        self.nacks.sort(key=lambda x: x[0])
        for sack in sacks:
            start, end = sack
            while nacks_index < len(self.nacks):
                if self.nacks[nacks_index][0] >= end:
                    break
                elif self.nacks[nacks_index][1] <= end and self.nacks[nacks_index][0] >= start:
                    new_acks.append(self.nacks[nacks_index])
                nacks_index+=1
                
        
        # update self.nacks (inflight) and self.sacks (acknowledged sequences)
        for ack in new_acks:
            self.sacks.append(ack)
            self.nacks.remove(ack)
            off_flight += (ack[1]-ack[0])
            if ack in self.duplicate_count:
                del self.duplicate_count[ack]
                
 
        # update self.base
        if sacks[0][0]==0:
            self.base = sacks[0][1]
        else:
            self.base = 0
        
        # count for dupACKs
        ## count gaps in self.nacks (inflight)
        
        if sacks[0][0] != 0:
            end = 0
            while True:
                start = end
                end = min(start+payload_size,self.data_len)
                seq = (start, end)
                if seq in self.nacks:
                    if seq not in self.duplicate_count:
                        self.duplicate_count[seq] = 1
                    else:
                        self.duplicate_count[seq] += 1
                        if(self.duplicate_count[seq] >= 3):
                            if first_dupACK==None: first_dupACK=seq 
                            del self.duplicate_count[seq]
                            self.nacks.remove(seq)
                            off_flight += (seq[1]-seq[0])
                            self.retransmit_queue.append(seq)
                else:
                    self.record_miss.add(seq)
                if end == sacks[0][0]:
                    break
                
        ## count gaps in sacks
        size = len(sacks)
        for i in range(size-1):
            end = sacks[i][1]
            while True:
                start = end 
                end = min(start+payload_size,self.data_len)
                seq = (start,end)
                if seq in self.nacks:
                    if seq not in self.duplicate_count:
                        self.duplicate_count[seq] = 1
                    else:
                        self.duplicate_count[seq] += 1
                        if(self.duplicate_count[seq] >= 3):
                            if first_dupACK==None: first_dupACK=seq 
                            del self.duplicate_count[seq]
                            self.nacks.remove(seq)
                            off_flight += (seq[1]-seq[0])
                            self.retransmit_queue.append(seq)
                else:
                    self.record_miss.add(seq)
                if end == sacks[i+1][0]:
                    break
                
        
        self.retransmit_queue.sort(key=lambda x: x[0])
        if self.base >= self.data_len:
            self.complete = True
            
        
        self.inflight -= off_flight
        self.MAXCWND = max(self.cwnd, self.inflight+payload_size)
        
        # CCA 
        for ack in new_acks:
            if ack in self.rtt_time:
                sampleRTT = ack_receive_time - self.rtt_time[ack]
                print(f"sampleRTT: {sampleRTT}")
                self.estimatedRTT = 0.875*self.estimatedRTT+0.125*sampleRTT
                self.devRTT = 0.75*self.devRTT + 0.25*abs(sampleRTT-self.estimatedRTT)
                self.rto = self.estimatedRTT + 4*self.devRTT
                break
            
        if self.state == self.SLOW_START:
            print("in slow start")
            if first_dupACK!=None:
                print("go to fast recovery")
                print(f"before: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
                self.state = self.FAST_RECOVERY
                self.fast_recovery_packet = first_dupACK
                self.ssthresh = max(self.cwnd//2, packet_size)
                self.cwnd = self.ssthresh + 3*payload_size
                print(f"after: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
            else:
                if new_acks:
                    print(f"{len(new_acks)} new acks")
                    print(f"before: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
                    self.cwnd += payload_size
                    if self.cwnd >= self.ssthresh:
                        print("go to congestion avoidance")
                        self.state = self.CONGEST_AVOID 
                    print(f"after: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")  
        elif self.state == self.CONGEST_AVOID:
            print("in congestion avoidance")
            if first_dupACK!=None:
                print("go to fast recovery")
                print(f"before: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
                self.state = self.FAST_RECOVERY
                self.fast_recovery_packet = first_dupACK
                self.ssthresh = max(self.cwnd//2, packet_size)
                self.cwnd = self.ssthresh + 3*payload_size
                print(f"after: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
            else:
                if new_acks:
                    print(f"{len(new_acks)} new acks")
                    print(f"before: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
                    self.cwnd += (payload_size*payload_size)//self.cwnd
                    print(f"after: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
        elif self.state == self.FAST_RECOVERY:
            print("in fast recovery")
            if new_acks:
                if self.fast_recovery_packet in new_acks:
                    print("get the target sequence")
                    print("go to congestion avoidance")
                    self.state = self.CONGEST_AVOID
                    print(f"before: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
                    self.cwnd = self.ssthresh
                    print(f"after: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
                else:
                    print("get other new acks")
                    print(f"before: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
                    #self.cwnd = self.MAXCWND
                    print(f"inflight: {self.inflight}")
                    print(f"after: ssthresh: {self.ssthresh}\tcwnd: {self.cwnd}")
            else:
                pass 
        
        print("--------------------")
            
        return off_flight

    def send(self, packet_id: int) -> Optional[Tuple[int, int]]:
        '''Called just before we are going to send a data packet. Should
        return the range of sequence numbers we should send. If there
        are no more bytes to send, returns a zero range (i.e. the two
        elements of the tuple are equal). Return None if there are no
        more bytes to send, and _all_ bytes have been
        acknowledged. Note: The range should not be larger than
        `payload_size` or contain any bytes that have already been
        acknowledged

        '''

        # TODO
        if self.complete:   return None
        if self.timeout_queue:
            print("timeout retransmit")
            seq = self.timeout_queue[0]
            self.timeout_queue.remove(seq)
            self.nacks.append(seq)
            self.inflight += (seq[1]-seq[0])
            return seq
        
        if self.retransmit_queue:
            print("fast retransmit")
            seq = self.retransmit_queue[0]
            self.retransmit_queue.remove(seq)
            self.nacks.append(seq) 
            self.inflight += (seq[1]-seq[0])
            return seq
        
        start = self.nextseqnum
        end = min(self.nextseqnum+payload_size, self.data_len)
        
        if start > self.data_len:
            return (start, start)
        
        seq = (start, end)
        self.nextseqnum += payload_size
        self.nacks.append(seq)
        self.rtt_time[seq] = time.perf_counter()
        self.inflight += (seq[1]-seq[0])
        return seq



    def get_cwnd(self) -> int:
        # TODO
        return self.cwnd

    def get_rto(self) -> float:
        # TODO
        return self.rto

def start_receiver(ip: str, port: int):
    '''Starts a receiver thread. For each source address, we start a new
    `Receiver` class. When a `fin` packet is received, we call the
    `finish` function of that class.

    We start listening on the given IP address and port. By setting
    the IP address to be `0.0.0.0`, you can make it listen on all
    available interfaces. A network interface is typically a device
    connected to a computer that interfaces with the physical world to
    send/receive packets. The WiFi and ethernet cards on personal
    computers are examples of physical interfaces.

    Sometimes, when you start listening on a port and the program
    terminates incorrectly, it might not release the port
    immediately. It might take some time for the port to become
    available again, and you might get an error message saying that it
    could not bind to the desired port. In this case, just pick a
    different port. The old port will become available soon. Also,
    picking a port number below 1024 usually requires special
    permission from the OS. Pick a larger number. Numbers in the
    8000-9000 range are conventional.

    Virtual interfaces also exist. The most common one is `localhost',
    which has the default IP address of `127.0.0.1` (a universal
    constant across most machines). The Mahimahi network emulator also
    creates virtual interfaces that behave like real interfaces, but
    really only emulate a network link in software that shuttles
    packets between different virtual interfaces.

    '''

    receivers: Dict[str, Receiver] = {}

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((ip, port))

        while True:
            data, addr = server_socket.recvfrom(packet_size)
            if addr not in receivers:
                receivers[addr] = Receiver()

            received = json.loads(data.decode())
            if received["type"] == "data":
                # Format check. Real code will have much more
                # carefully designed checks to defend against
                # attacks. Can you think of ways to exploit this
                # transport layer and cause problems at the receiver?
                # This is just for fun. It is not required as part of
                # the assignment.
                assert type(received["seq"]) is list
                assert type(received["seq"][0]) is int and type(received["seq"][1]) is int
                assert type(received["payload"]) is str
                assert len(received["payload"]) <= payload_size

                # Deserialize the packet. Real transport layers use
                # more efficient and standardized ways of packing the
                # data. One option is to use protobufs (look it up)
                # instead of json. Protobufs can automatically design
                # a byte structure given the data structure. However,
                # for an internet standard, we usually want something
                # more custom and hand-designed.
                sacks, app_data = receivers[addr].data_packet(tuple(received["seq"]), received["payload"])
                # Note: we immediately write the data to file
                #receivers[addr][1].write(app_data)
                print(f"Received seq: {received['seq']}, id: {received['id']}, sending sacks: {sacks}")
                # Send the ACK
                server_socket.sendto(json.dumps({"type": "ack", "sacks": sacks, "id": received["id"]}).encode(), addr)


            elif received["type"] == "fin":
                receivers[addr].finish()
                del receivers[addr]

            else:
                assert False

def start_sender(ip: str, port: int, data: str, recv_window: int, simloss: float):
    sender = Sender(len(data))

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        # So we can receive messages
        client_socket.connect((ip, port))
        # When waiting for packets when we call receivefrom, we
        # shouldn't wait more than 500ms

        # Number of bytes that we think are inflight. We are only
        # including payload bytes here, which is different from how
        # TCP does things
        inflight = 0
        packet_id  = 0
        wait = False

        while True:
            # Get the congestion condow
            cwnd = sender.get_cwnd()

            # Do we have enough room in recv_window to send an entire
            # packet?
            if inflight + packet_size <= min(recv_window, cwnd) and not wait:
                seq = sender.send(packet_id)
                if seq is None:
                    # We are done sending
                    client_socket.send('{"type": "fin"}'.encode())
                    break
                elif seq[1] == seq[0]:
                    # No more packets to send until loss happens. Wait
                    wait = True
                    continue

                assert seq[1] - seq[0] <= payload_size
                assert seq[1] <= len(data)

                # Simulate random loss before sending packets
                if random.random() < simloss:
                    pass
                else:
                    # Send the packet
                    client_socket.send(
                        json.dumps(
                            {"type": "data", "seq": seq, "id": packet_id, "payload": data[seq[0]:seq[1]]}
                        ).encode())
                    print(f"send seq: {seq}\t,id: {packet_id}")

                inflight += seq[1] - seq[0]
                print(f"inflight(+): {inflight}")
                packet_id += 1

            else:
                wait = False
                # Wait for ACKs
                try:
                    rto = sender.get_rto()
                    client_socket.settimeout(rto)
                    received_bytes = client_socket.recv(packet_size)
                    received = json.loads(received_bytes.decode())
                    assert received["type"] == "ack"

                    if random.random() < simloss:
                        continue
                    

                    inflight -= sender.ack_packet(received["sacks"], received["id"])
                    print(f"inflight(-): {inflight}")
                    assert inflight >= 0
                except socket.timeout:
                    inflight = 0
                    print("Timeout")
                    sender.timeout()


def main():
    parser = argparse.ArgumentParser(description="Transport assignment")
    parser.add_argument("role", choices=["sender", "receiver"], help="Role to play: 'sender' or 'receiver'")
    parser.add_argument("--ip", type=str, required=True, help="IP address to bind/connect to")
    parser.add_argument("--port", type=int, required=True, help="Port number to bind/connect to")
    parser.add_argument("--sendfile", type=str, required=False, help="If role=sender, the file that contains data to send")
    parser.add_argument("--recv_window", type=int, default=15000000, help="Receive window size in bytes")
    parser.add_argument("--simloss", type=float, default=0.0, help="Simulate packet loss. Provide the fraction of packets (0-1) that should be randomly dropped")

    args = parser.parse_args()

    if args.role == "receiver":
        start_receiver(args.ip, args.port)
    else:
        if args.sendfile is None:
            print("No file to send")
            return

        with open(args.sendfile, 'r') as f:
            data = f.read()
            start_sender(args.ip, args.port, data, args.recv_window, args.simloss)

if __name__ == "__main__":
    main()

