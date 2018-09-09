import binascii
import json
import os
import subprocess

import blocks
from web3 import Web3
from genesis_state import genesis_state



abi = json.loads('[{"constant":false,"inputs":[{"name":"_shard_ID","type":"uint256"},{"name":"_sendGas","type":"uint256"},{"name":"_sendToAddress","type":"address"},{"name":"_data","type":"bytes"}],"name":"send","outputs":[],"payable":true,"stateMutability":"payable","type":"function"},{"anonymous":false,"inputs":[{"indexed":true,"name":"shard_ID","type":"uint256"},{"indexed":false,"name":"sendGas","type":"uint256"},{"indexed":false,"name":"sendFromAddress","type":"address"},{"indexed":false,"name":"sendToAddress","type":"address"},{"indexed":false,"name":"value","type":"uint256"},{"indexed":false,"name":"data","type":"bytes"},{"indexed":true,"name":"base","type":"uint256"},{"indexed":false,"name":"TTL","type":"uint256"}],"name":"SentMessage","type":"event"}]')

web3 = Web3()

vladvm_path = './vladvm-ubuntu'
if(os.getenv("_system_type")):
    vladvm_path = './vladvm-macos'

contract = web3.eth.contract(address='0x000000000000000000000000000000000000002A', abi=abi)
tx = contract.functions.send(1, 300000, '0xDeaDbeefdEAdbeefdEadbEEFdeadbeEFdEaDbeeF', '0x1234').buildTransaction({ "gas": 3000000, "gasPrice": "0x2", "nonce": "0x0", "value": 5 })

signed = web3.eth.account.signTransaction(tx, '0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318')
address = web3.eth.account.privateKeyToAccount('0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318').address

def format_transaction(tx, signed):
    return {
        "gas": hex(tx["gas"]),
        "gasPrice": tx["gasPrice"],
        "hash": signed["hash"].hex(),
        "input": tx["data"],
        "nonce": tx["nonce"],
        "r": hex(signed["r"]),
        "s": hex(signed["s"]),
        "v": hex(signed["v"]),
        "to": tx["to"],
        "value": hex(tx["value"]),
    }

vm_state = {}
vm_state["env"] = genesis_state["env"]
vm_state["pre"] = genesis_state["pre"]

transactions = [
    format_transaction(tx, signed),
    {
        "gas": "0x5208",
        "gasPrice": "0x2",
        "hash": "0x0557bacce3375c98d806609b8d5043072f0b6a8bae45ae5a67a00d3a1a18d673",
        "input": "0x",
        "nonce": "0x0",
        "r": "0x9500e8ba27d3c33ca7764e107410f44cbd8c19794bde214d694683a7aa998cdb",
        "s": "0x7235ae07e4bd6e0206d102b1f8979d6adab280466b6a82d2208ee08951f1f600",
        "to": "0x8a8eafb1cf62bfbeb1741769dae1a9dd47996192",
        "v": "0x1b",
        "value": "0x1"
    }
]



# The “vm state” is really the “pre” part of what we send to vladvm. 
# The “env” stuff is constant
# the “transactions” list is a list of transactions that come from the 
#   mempool (originally a file full of test data?) and ones that are constructed from 
#   `MessagePayload`s. (This is done via `web3.eth.account.signTransaction(…)`.)
# function apply(vm_state, [tx], mapping(S => received)) -> (vm_state, mapping(S => received) ) 
def apply_to_state(pre_state=vm_state, tx=[]): #, receivedMap):
    # open a process
    vladvm = subprocess.Popen([vladvm_path, 'apply', '/dev/stdin'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    # pipe state into that process 
    out = vladvm.communicate(json.dumps(vm_state).encode())[0].decode('utf-8')
    
    result = json.loads(out)
    
    for receipt in result['receipts']:
        if receipt['logs'] is not None:
            for log in receipt['logs']:
                log['topics'] = [binascii.unhexlify(t[2:]) for t in log['topics']]
                log['data'] = binascii.unhexlify(log['data'][2:])
            print(contract.events.SentMessage().processReceipt(receipt))
    # return new_state;

apply_to_state(vm_state, transactions, 