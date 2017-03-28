"""Floating IP config utilities."""

import fixtures


class CreateAssociateFip(fixtures.Fixture):

    """Create and associate a floating IP to the Virtual Machine."""

    def __init__(self, inputs, fip_fixture, vn_id, vm_id):
        self.inputs = inputs
        self.logger = self.inputs.logger
        self.fip_fixture = fip_fixture
        self.vn_id = vn_id
        self.vm_id = vm_id

    def setUp(self):
        self.logger.info("Create associate FIP")
        super(CreateAssociateFip, self).setUp()
        self.fip_id = self.fip_fixture.create_and_assoc_fip(
            self.vn_id, self.vm_id)

    def cleanUp(self):
        self.logger.info("Disassociationg FIP")
        super(CreateAssociateFip, self).cleanUp()
        self.fip_fixture.disassoc_and_delete_fip(self.fip_id)
