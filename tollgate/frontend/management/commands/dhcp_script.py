"""
tollgate management command: dhcp notify script
Copyright 2008-2012 Michael Farrell

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from django.core.management.base import BaseCommand, CommandError
from tollgate.frontend.models import sync_user_connections, NetworkHost, utcnow
from django.core.exceptions import ObjectDoesNotExist
import string


class Command(BaseCommand):
	args = '<add|del> <mac address> <ip> [hostname]'
	help = """
		Recieves notifications of changes to DHCP servers.
		
		Accepts options in the same format as dnsmasq's dhcp-script option.
		
		Also can be used with ISC DHCPd with some tricks.
	"""

	def handle(self, *args, **options):
		if len(args) < 3:
			print "Error: you must supply at least three arguments."
			return
			
		action = args[0].strip().lower()
		mac = args[1].strip().lower()
		ip = args[2].strip()
		hostname = args[3].strip() if len(args) >= 4 else ''
		if ':' in mac:
			# handle no leading zero on octets split by :
			mac = ''.join([('%02x' % int(x, 16)) for x in mac.split(':')])
		elif '-' in mac:
			# handle no leading zero on octets split by -
			mac = ''.join([('%02x' % int(x, 16)) for x in mac.split('-')])
		
		# last resort, and backup filter to make it probably valid...
		mac2 = ''
		for c in mac:
			# remove non-hex characters.
			if c in string.hexdigits:
				mac2 += c
		mac = mac2
		del mac2
		
		if len(mac) != 12:
			# not the right number of characters.
			print "Error: MAC address must be 6 base16 encoded bytes (12 bytes" + \
				" total)."
			print mac
			return

		# filter hostname (problem with Nintendo 3DS sending hostname with spaces)
		# django has some issue with dealing with spaces in arguments?
		hostname2 = ''
		for c in hostname:
			if (c in string.letters) or (c in string.digits):
				hostname2 += c

		hostname = hostname2
		del hostname2

		# TODO: Validate IP address
		
		if action in ('add', 'del'):
			try:
				# see if host exists
				host = NetworkHost.objects.get(mac_address__iexact=mac)
				host.ip_address = ip
				host.online = action == 'add'
				host.computer_name = hostname
				host.save()
			except ObjectDoesNotExist:
				# create new host entry
				host = NetworkHost.objects.create(
					mac_address=mac,
					computer_name=hostname,
					first_connection=utcnow(),
					online=action == 'add',
					ip_address=ip
				)
			# now refresh the owner's hosts, if any.
			if host.user_profile != None:
				sync_user_connections(host.user_profile)
				
			print "%s host: mac=%s; ip=%s; hostname=%s" % (action, mac, ip, hostname)
		else:
			print "Error: unknown action %r" % action
			return
		

