# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: power_capper.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x12power_capper.proto\"\x1e\n\tCap_Input\x12\x11\n\tpower_cap\x18\x01 \x01(\x01\"\x1c\n\nCap_Output\x12\x0e\n\x06status\x18\x01 \x01(\x08\x32\x35\n\x0bPowerCapper\x12&\n\tcap_power\x12\n.Cap_Input\x1a\x0b.Cap_Output\"\x00\x62\x06proto3')



_CAP_INPUT = DESCRIPTOR.message_types_by_name['Cap_Input']
_CAP_OUTPUT = DESCRIPTOR.message_types_by_name['Cap_Output']
Cap_Input = _reflection.GeneratedProtocolMessageType('Cap_Input', (_message.Message,), {
  'DESCRIPTOR' : _CAP_INPUT,
  '__module__' : 'power_capper_pb2'
  # @@protoc_insertion_point(class_scope:Cap_Input)
  })
_sym_db.RegisterMessage(Cap_Input)

Cap_Output = _reflection.GeneratedProtocolMessageType('Cap_Output', (_message.Message,), {
  'DESCRIPTOR' : _CAP_OUTPUT,
  '__module__' : 'power_capper_pb2'
  # @@protoc_insertion_point(class_scope:Cap_Output)
  })
_sym_db.RegisterMessage(Cap_Output)

_POWERCAPPER = DESCRIPTOR.services_by_name['PowerCapper']
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _CAP_INPUT._serialized_start=22
  _CAP_INPUT._serialized_end=52
  _CAP_OUTPUT._serialized_start=54
  _CAP_OUTPUT._serialized_end=82
  _POWERCAPPER._serialized_start=84
  _POWERCAPPER._serialized_end=137
# @@protoc_insertion_point(module_scope)
