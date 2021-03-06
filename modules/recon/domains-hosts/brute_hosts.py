from recon.core.module import BaseModule
from recon.mixins.resolver import ResolverMixin
from recon.mixins.threads import ThreadingMixin
import dns.resolver
import os

class Module(BaseModule, ResolverMixin, ThreadingMixin):

    meta = {
        'name': 'DNS Hostname Brute Forcer',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'description': 'Brute forces host names using DNS. Updates the \'hosts\' table with the results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (
            ('wordlist', os.path.join(BaseModule.data_path, 'hostnames.txt'), True, 'path to hostname wordlist'),
        ),
    }

    def module_run(self, domains):
        with open(self.options['wordlist']) as fp:
            words = fp.read().split()
        resolver = self.get_resolver()
        for domain in domains:
            self.heading(domain, level=0)
            try:
                answers = resolver.query('*.%s' % (domain))
                self.output('Wildcard DNS entry found for \'%s\'. Cannot brute force hostnames.' % (domain))
                continue
            except (dns.resolver.NoNameservers, dns.resolver.Timeout):
                self.error('Invalid nameserver.')
                continue
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                self.verbose('No Wildcard DNS entry found.')
            self.thread(words, domain, resolver)

    def module_thread(self, word, domain, resolver):
        max_attempts = 3
        attempt = 0
        while attempt < max_attempts:
            host = '%s.%s' % (word, domain)
            try:
                answers = resolver.query(host)
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                self.verbose('%s => No record found.' % (host))
            except dns.resolver.Timeout:
                self.verbose('%s => Request timed out.' % (host))
                attempt += 1
                continue
            else:
                # process answers
                for answer in answers.response.answer:
                    for rdata in answer:
                        if rdata.rdtype in (1, 5):
                            if rdata.rdtype == 1:
                                self.alert('%s => (A) %s - Host found!' % (host, host))
                            if rdata.rdtype == 5:
                                cname = rdata.target.to_text()[:-1]
                                self.alert('%s => (CNAME) %s - Host found!' % (host, cname))
                                self.add_hosts(cname)
                            # add the host in case a CNAME exists without an A record
                            self.add_hosts(host)
            # break out of the loop
            attempt = max_attempts
