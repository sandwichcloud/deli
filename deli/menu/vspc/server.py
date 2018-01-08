#!/usr/bin/env python3
# Copyright (c) 2017 VMware Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import asyncio
import base64
import functools
import logging
import os

from deli.menu.vspc import async_telnet
from deli.menu.vspc.async_telnet import IAC, SB, SE, WILL, WONT, DONT, DO
from deli.menu.vspc.vm_client import VMClient

BINARY = bytes([0])  # 8-bit data path
SGA = bytes([3])  # suppress go ahead
VMWARE_EXT = bytes([232])

KNOWN_SUBOPTIONS_1 = bytes([0])
KNOWN_SUBOPTIONS_2 = bytes([1])
VMOTION_BEGIN = bytes([40])
VMOTION_GOAHEAD = bytes([41])
VMOTION_NOTNOW = bytes([43])
VMOTION_PEER = bytes([44])
VMOTION_PEER_OK = bytes([45])
VMOTION_COMPLETE = bytes([46])
VMOTION_ABORT = bytes([48])
VM_VC_UUID = bytes([80])
GET_VM_VC_UUID = bytes([81])
VM_NAME = bytes([82])
GET_VM_NAME = bytes([83])
DO_PROXY = bytes([70])
WILL_PROXY = bytes([71])
WONT_PROXY = bytes([73])

SUPPORTED_OPTS = (KNOWN_SUBOPTIONS_1 + KNOWN_SUBOPTIONS_2 + VMOTION_BEGIN +
                  VMOTION_GOAHEAD + VMOTION_NOTNOW + VMOTION_PEER +
                  VMOTION_PEER_OK + VMOTION_COMPLETE + VMOTION_ABORT +
                  VM_VC_UUID + GET_VM_VC_UUID + VM_NAME + GET_VM_NAME +
                  DO_PROXY + WILL_PROXY + WONT_PROXY)


class VSPCServer(object):
    def __init__(self, uri):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.uri = uri
        self.sock_to_client = {}

        self.server = None
        self.loop = None

    async def handle_known_suboptions(self, writer, data):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        self.logger.debug("<< %s KNOWN-SUBOPTIONS-1 %s", peer, data)
        self.logger.debug(">> %s KNOWN-SUBOPTIONS-2 %s", peer, SUPPORTED_OPTS)
        writer.write(IAC + SB + VMWARE_EXT + KNOWN_SUBOPTIONS_2 +
                     SUPPORTED_OPTS + IAC + SE)
        self.logger.debug(">> %s GET-VM-NAME", peer)
        writer.write(IAC + SB + VMWARE_EXT + GET_VM_NAME + IAC + SE)
        await writer.drain()

    async def handle_do_proxy(self, writer, data):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        dir, uri = data[0], data[1:].decode('ascii')
        self.logger.debug("<< %s DO-PROXY %c %s", peer, dir, uri)
        if chr(dir) != 'C' or uri != self.uri:
            self.logger.debug(">> %s WONT-PROXY", peer)
            writer.write(IAC + SB + VMWARE_EXT + WONT_PROXY + IAC + SE)
            await writer.drain()
            writer.close()
        else:
            self.logger.debug(">> %s WILL-PROXY", peer)
            writer.write(IAC + SB + VMWARE_EXT + WILL_PROXY + IAC + SE)
            await writer.drain()

    def handle_vm_name(self, socket, writer, data):
        peer = socket.getpeername()
        vm_name = data.decode('ascii')
        self.logger.debug("<< %s VM-NAME %s", peer, vm_name)
        self.sock_to_client[socket] = VMClient(vm_name, writer)

    async def handle_vmotion_begin(self, writer, data):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        self.logger.debug("<< %s VMOTION-BEGIN %s", peer, data)
        secret = os.urandom(4)
        self.logger.debug(">> %s VMOTION-GOAHEAD %s %s", peer, data, secret)
        writer.write(IAC + SB + VMWARE_EXT + VMOTION_GOAHEAD +
                     data + secret + IAC + SE)
        await writer.drain()

    async def handle_vmotion_peer(self, writer, data):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        self.logger.debug("<< %s VMOTION-PEER %s", peer, data)
        self.logger.debug("<< %s VMOTION-PEER-OK %s", peer, data)
        writer.write(IAC + SB + VMWARE_EXT + VMOTION_PEER_OK + data + IAC + SE)
        await writer.drain()

    def handle_vmotion_complete(self, socket, data):
        peer = socket.getpeername()
        self.logger.debug("<< %s VMOTION-COMPLETE %s", peer, data)

    async def handle_do(self, writer, opt):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        self.logger.debug("<< %s DO %s", peer, opt)
        if opt in (BINARY, SGA):
            self.logger.debug(">> %s WILL", peer)
            writer.write(IAC + WILL + opt)
            await writer.drain()
        else:
            self.logger.debug(">> %s WONT", peer)
            writer.write(IAC + WONT + opt)
            await writer.drain()

    async def handle_will(self, writer, opt):
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        self.logger.debug("<< %s WILL %s", peer, opt)
        if opt in (BINARY, SGA, VMWARE_EXT):
            self.logger.debug(">> %s DO", peer)
            writer.write(IAC + DO + opt)
            await writer.drain()
        else:
            self.logger.debug(">> %s DONT", peer)
            writer.write(IAC + DONT + opt)
            await writer.drain()

    async def option_handler(self, cmd, opt, writer, data=None):
        socket = writer.get_extra_info('socket')
        if cmd == SE and data[0:1] == VMWARE_EXT:
            vmw_cmd = data[1:2]
            if vmw_cmd == KNOWN_SUBOPTIONS_1:
                await self.handle_known_suboptions(writer, data[2:])
            elif vmw_cmd == DO_PROXY:
                await self.handle_do_proxy(writer, data[2:])
            elif vmw_cmd == VM_NAME:
                self.handle_vm_name(socket, writer, data[2:])
            elif vmw_cmd == VMOTION_BEGIN:
                await self.handle_vmotion_begin(writer, data[2:])
            elif vmw_cmd == VMOTION_PEER:
                await self.handle_vmotion_peer(writer, data[2:])
            elif vmw_cmd == VMOTION_COMPLETE:
                self.handle_vmotion_complete(socket, data[2:])
            else:
                self.logger.error("Unknown VMware cmd: %s %s", vmw_cmd, data[2:])
                writer.close()
        elif cmd == DO:
            await self.handle_do(writer, opt)
        elif cmd == WILL:
            await self.handle_will(writer, opt)

    async def process_packet(self, vm_client: VMClient, data):
        data = data.decode('ascii')

        if data.startswith('!!') is False:  # Make sure the data is a packet
            self.logger.warning("Received a bad packet from " + vm_client.vm_name)
            return
        else:
            data = data[2:]

        packet_code, data = data.split('#')  # Packet code and data is split by #

        if len(data) > 0:
            data = base64.b64decode(data).decode('ascii')  # Packet data is base64 encoded

        await vm_client.process_packets(packet_code, data)

    async def handle_telnet(self, reader, writer):
        opt_handler = functools.partial(self.option_handler, writer=writer)
        telnet = async_telnet.AsyncTelnet(reader, opt_handler)
        socket = writer.get_extra_info('socket')
        peer = socket.getpeername()
        self.logger.info("%s connected", peer)
        data = await telnet.read_line()
        vm_client = self.sock_to_client.get(socket)
        if vm_client is None:
            self.logger.error("%s didn't present UUID", peer)
            writer.close()
            return
        try:
            while data:
                await self.process_packet(vm_client, data)
                data = await telnet.read_line()
        except Exception:
            self.logger.exception("Raised exception while processing packet")
        finally:
            self.sock_to_client.pop(socket, None)
        self.logger.info("%s disconnected", peer)
        writer.close()

    def start(self):
        self.loop = asyncio.get_event_loop()
        ssl_context = None
        # if CONF.cert:
        #     ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        #     ssl_context.load_cert_chain(certfile=CONF.cert, keyfile=CONF.key)
        coro = asyncio.start_server(self.handle_telnet,
                                    '0.0.0.0',
                                    13370,
                                    ssl=ssl_context,
                                    loop=self.loop)
        self.server = self.loop.run_until_complete(coro)

        # Serve requests until Ctrl+C is pressed
        self.logger.info("Serving on %s", self.server.sockets[0].getsockname())
        self.loop.run_forever()

    def stop(self):
        # Close the server
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()
