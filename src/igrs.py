from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from re import match
import socket

domain = "acme.pt"
registered_users = {}
kpi_metrics = {
   "Chamadas atendidas automaticamente": 0,
   "Conferências realizadas": 0,
}

def normalize_uri(uri):
   """Normalize a SIP URI by stripping display names and parameters."""
   result = match(r".*<([^>]+)>.*", uri)
   return result.group(1) if result else uri

class SIPServerProtocol(DatagramProtocol):
   def __init__(self):
       self.pending_calls = {}

   def get_local_ip(self):
       """Get the local IP address of the server."""
       s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       s.settimeout(0)
       try:
           s.connect(('10.254.254.254', 1))  # Arbitrary IP to get local IP
           ip = s.getsockname()[0]
       except Exception:
           ip = '127.0.0.1'  # Fallback
       finally:
           s.close()
       return ip

   def datagramReceived(self, data, addr):
       message = data.decode()
       print(f"Mensagem SIP recebida de {addr}: {message}")

       try:
           method, uri, headers, body = self.parse_sip_message(message)

           if method == "REGISTER":
               self.handle_register(headers, addr)
           elif method == "MESSAGE":
               self.handle_message(headers, body, addr)
           elif method == "INVITE":
               self.handle_invite(headers, addr)
           elif method == "BYE":
               self.handle_bye(headers, addr)
           elif method == "OPTIONS":
               self.handle_options(headers, addr)
           elif method == "CANCEL":
               self.handle_cancel(headers, addr)
           elif method == "ACK":
               self.handle_ack(headers, addr)
           else:
               self.send_sip_response(501, "Not Implemented", addr, headers=headers)
       except Exception as e:
           print(f"Erro ao processar a mensagem SIP: {e}")

   def parse_sip_message(self, message):
       """Parse SIP message into method, URI, headers, and body"""
       try:
           print(f"Parsing SIP message:\n{message}")
           lines = message.split("\r\n")
           method, uri, protocol = lines[0].split(" ")
           headers = {}
           for line in lines[1:]:
               if ": " in line:
                   key, value = line.split(": ", 1)
                   headers[key] = value
               elif line == "":
                   break
           body = "\r\n".join(lines[lines.index("") + 1:]) if "" in lines else ""
           return method, uri, headers, body
       except ValueError as ve:
           print(f"ValueError while parsing SIP message: {ve}")
           raise
       except Exception as e:
           print(f"Unexpected error while parsing SIP message: {e}")
           raise

   def send_sip_response(self, code, reason, addr, headers=None, body=""):
       """Send a SIP response following RFC 3261"""
       response = f"SIP/2.0 {code} {reason}\r\n"

       if headers and "Via" in headers:
           response += f"Via: {headers['Via']}\r\n"
       if headers and "Call-ID" in headers:
           response += f"Call-ID: {headers['Call-ID']}\r\n"
       if headers and "CSeq" in headers:
           response += f"CSeq: {headers['CSeq']}\r\n"
       if headers and "From" in headers:
           response += f"From: {headers['From']}\r\n"
       if headers and "To" in headers:
           response += f"To: {headers['To']};tag=1234\r\n"

       if code == 200 and "From" in headers:
           response += f"Contact: {headers['From']}\r\n"

       response += f"Content-Length: {len(body)}\r\n\r\n{body}"
       print(f"Enviando resposta SIP para {addr}:\n{response}")
       self.transport.write(response.encode(), addr)

   def handle_register(self, headers, addr):
       """Handle SIP REGISTER"""
       aor = headers.get("From")
       contact = headers.get("Contact", "")
       expires = headers.get("Expires", "3600")
       rtp_port = headers.get("RTP-Port", "8888")

       if domain not in aor:
           self.send_sip_response(403, "Forbidden", addr, headers=headers)
           return

       if expires == "0":
           if aor in registered_users:
               del registered_users[aor]
               self.send_sip_response(200, "OK - De-registered", addr, headers=headers)
           else:
               self.send_sip_response(404, "Not Found", addr, headers=headers)
           return

       registered_users[aor] = {"status": "registered", "addr": addr, "contact": contact, "rtp": rtp_port}
       print(f"User registered: {aor} -> {addr},{rtp_port}")
       self.send_sip_response(200, "OK - Registered", addr, headers=headers)

   def handle_invite(self, headers, addr):
       call_id = headers.get("Call-ID")
       to_uri = normalize_uri(headers.get("To"))
       from_uri = normalize_uri(headers.get("From"))

       print(f"Normalized To URI: {to_uri}")
       print(f"Normalized From URI: {from_uri}")
       print(f"Registered users: {registered_users}")

       normalized_users = {normalize_uri(k): v for k, v in registered_users.items()}

       if to_uri in normalized_users:
           target_addr = normalized_users[to_uri]["addr"]
           print(f"Forwarding INVITE to {target_addr}")
           self.transport.write(self.create_forwarded_invite(headers), target_addr)

           self.pending_calls[call_id] = reactor.callLater(
               30, self.auto_answer_call, headers, addr
           )

           sdp_body = self.generate_sdp_offer(normalized_users[to_uri]["rtp"])
           self.transport.write(self.create_forwarded_invite(headers, body=sdp_body), target_addr)
       else:
           print(f"{to_uri} not found in registered users.")
           self.send_sip_response(404, "Not Found", addr, headers=headers)

   def generate_sdp_offer(self, rtp_port):
       """Generate SDP with the specified RTP port"""
       sdp_body = (
           "v=0\r\n"
           f"o=- 0 0 IN IP4 {self.get_local_ip()}\r\n"  
           "s=Call\r\n"
           f"c=IN IP4 {self.get_local_ip()}\r\n"
           "t=0 0\r\n"
           f"m=audio {rtp_port} RTP/AVP 0\r\n"  
           f"a=rtpmap:0 PCMU/{rtp_port}\r\n"  
       )
       return sdp_body

   def handle_bye(self, headers, addr):
       """Handle SIP BYE request."""
       print("Call terminated.")
       self.send_sip_response(200, "OK", addr, headers=headers)

   def handle_options(self, headers, addr):
       """Handle SIP OPTIONS request."""
       print("Server status check (OPTIONS).")
       response_body = "SIP/2.0 200 OK"
       self.send_sip_response(200, "OK", addr, headers=headers, body=response_body)

   def handle_cancel(self, headers, addr):
       """Handle SIP CANCEL request."""
       print("Call cancelled.")
       self.send_sip_response(200, "OK", addr, headers=headers)

   def handle_ack(self, headers, addr):
       """Handle SIP ACK request."""
       print("Acknowledgement received.")
       self.send_sip_response(200, "OK", addr, headers=headers)

   def create_forwarded_invite(self, headers, body=""):
       """Create a forwarded INVITE request to the target (called client)."""
       invite = f"INVITE {normalize_uri(headers['To'])} SIP/2.0\r\n"
       invite += f"Via: {headers['Via']}\r\n"
       invite += f"From: {headers['From']}\r\n"
       invite += f"To: {headers['To']}\r\n"
       invite += f"Call-ID: {headers['Call-ID']}\r\n"
       invite += f"CSeq: {headers['CSeq']}\r\n"
       invite += f"Contact: {headers['Contact']}\r\n"
       invite += "Content-Type: application/sdp\r\n" if body else ""
       invite += f"Content-Length: {len(body)}\r\n\r\n{body}"
       return invite.encode()
   
# Start SIP server on UDP port 5060
reactor.listenUDP(5060, SIPServerProtocol(), interface="0.0.0.0")
print("Servidor SIP iniciado na porta UDP 5060")
reactor.run()
