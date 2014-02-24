import os
import time
import unittest
import subprocess
import resource
import sys
import tempfile
import shutil
import logging
import re

class GpuTest(object):

    def __init__(self,
                 has_single_card=False,
                 is_laptop=False,
                 has_intel=False,
                 intel_loaded=False,
                 has_amd=False,
                 fglrx_loaded=False,
                 radeon_loaded=False,
                 has_nvidia=False,
                 nouveau_loaded=False,
                 nvidia_loaded=False,
                 nvidia_enabled=False,
                 fglrx_enabled=False,
                 mesa_enabled=False,
                 prime_enabled=False,
                 pxpress_enabled=False,
                 has_changed=False,
                 has_removed_xorg=False,
                 has_regenerated_xorg=False,
                 has_selected_driver=False,
                 has_not_acted=True,
                 has_skipped_hybrid=False):
        self.has_single_card = has_single_card
        self.is_laptop = is_laptop
        self.has_intel = has_intel
        self.intel_loaded = intel_loaded
        self.has_amd = has_amd
        self.radeon_loaded = radeon_loaded
        self.fglrx_loaded = fglrx_loaded
        self.has_nvidia = has_nvidia
        self.nouveau_loaded = nouveau_loaded
        self.nvidia_loaded = nvidia_loaded
        self.nvidia_enabled = nvidia_enabled
        self.fglrx_enabled = fglrx_enabled
        self.mesa_enabled = mesa_enabled
        self.prime_enabled = prime_enabled
        self.pxpress_enabled = pxpress_enabled
        self.has_changed = has_changed
        self.has_removed_xorg = has_removed_xorg
        self.has_regenerated_xorg = has_regenerated_xorg
        self.has_selected_driver = has_selected_driver
        self.has_not_acted = has_not_acted
        self.has_skipped_hybrid = has_skipped_hybrid


class GpuManagerTest(unittest.TestCase):

    @classmethod
    def setUpClass(klass):
        #FIXME: remove this
        os.system('rm /media/caviar4/data/ubuntu/gpu_manager/tmp/*')
        klass.last_boot_file = tempfile.NamedTemporaryFile(mode='w', dir='/media/caviar4/data/ubuntu/gpu_manager/tmp/', delete=False)
        klass.last_boot_file.close()
        klass.new_boot_file = tempfile.NamedTemporaryFile(mode='w', dir='/media/caviar4/data/ubuntu/gpu_manager/tmp/', delete=False)
        klass.new_boot_file.close()
        klass.xorg_file = tempfile.NamedTemporaryFile(mode='w', dir='/media/caviar4/data/ubuntu/gpu_manager/tmp/', delete=False)
        klass.xorg_file.close()
        klass.fake_lspci = tempfile.NamedTemporaryFile(mode='w', dir='/media/caviar4/data/ubuntu/gpu_manager/tmp/', delete=False)
        klass.fake_lspci.close()
        klass.fake_modules = tempfile.NamedTemporaryFile(mode='w', dir='/media/caviar4/data/ubuntu/gpu_manager/tmp/', delete=False)
        klass.fake_modules.close()
        klass.fake_alternatives = tempfile.NamedTemporaryFile(mode='w', dir='/media/caviar4/data/ubuntu/gpu_manager/tmp/', delete=False)
        klass.fake_alternatives.close()
        klass.log = tempfile.NamedTemporaryFile(mode='w', dir='/media/caviar4/data/ubuntu/gpu_manager/tmp/', delete=False)
        klass.log.close()

        # Patterns
        klass.is_driver_loaded_pt = re.compile('Is (.+) loaded\? (.+)')
        klass.is_driver_enabled_pt = re.compile('Is (.+) enabled\? (.+)')
        klass.has_card_pt = re.compile('Has (.+)\? (.+)')
        klass.single_card_pt = re.compile('Single card detected.*')
        klass.is_laptop_pt = re.compile('Is laptop\? (.+)')
        klass.no_change_stop_pt = re.compile('No change - nothing to do')
        klass.has_changed_pt = re.compile('System configuration has changed')

        klass.selected_driver_pt = re.compile('Selecting (.+)')
        klass.removed_xorg_pt = re.compile('Removing xorg.conf. Path: .+')
        klass.regenerated_xorg_pt = re.compile('Regenerating xorg.conf. Path: .+')
        klass.not_modified_xorg_pt = re.compile('No need to modify xorg.conf. Path .+')
        klass.no_action_pt = re.compile('Nothing to do')
        klass.has_skipped_hybrid_pt = re.compile('Intel hybrid laptop - nothing to do')

    #@classmethod
    #def tearDownClass(klass):
    #    for file in (klass.last_boot_file,
    #                 klass.new_boot_file,
    #                 klass.fake_lspci,
    #                 klass.fake_modules,
    #                 klass.fake_alternatives,
    #                 klass.log):
    #        try:
    #            file.close()
    #        except:
    #            pass
            #shutil.copy(file.name, '/media/caviar4/data/ubuntu/gpu_manager/')
            #os.unlink(file.name)

    def setUp(self):
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.remove_xorg_conf()

    def tearDown(self):
        for file in (self.last_boot_file,
                     self.new_boot_file,
                     self.fake_lspci,
                     self.fake_modules,
                     self.fake_alternatives,
                     self.log,
                     self.xorg_file):
            target_dir = '/media/caviar4/data/ubuntu/gpu_manager/%s' % self.this_function_name
            try:
                file.close()
            except:
                pass
            try:
                os.mkdir(target_dir)
            except:
                pass
            try:
                shutil.copy(file.name, target_dir)
                os.unlink(file.name)
            except:
                pass

    def remove_xorg_conf(self):
        try:
            os.unlink(self.xorg_file.name)
        except:
            pass

    def exec_manager(self, fake_alternative, is_laptop=False):
        fake_laptop_arg = is_laptop and '--fake-laptop' or '--fake-desktop'
        os.system('/home/alberto/oem/nvidia/nvidia-common/ubuntu-drivers-common/share/hybrid/gpu-manager --dry-run '
                  '--last-boot-file %s '
                  '--fake-lspci %s '
                  '--xorg-conf-file %s '
                  '--fake-alternative %s '
                  '--fake-modules-path %s '
                  '--fake-alternatives-path %s '
                  '--new-boot-file %s '
                  '%s '
                  '--log %s ' % (self.last_boot_file.name,
                                 self.fake_lspci.name,
                                 self.xorg_file.name,
                                 fake_alternative,
                                 self.fake_modules.name,
                                 self.fake_alternatives.name,
                                 self.new_boot_file.name,
                                 fake_laptop_arg,
                                 self.log.name)
                  )

        # Remove xorg.conf
        self.remove_xorg_conf()

    def check_vars(self, *args, **kwargs):
        gpu_test = GpuTest(**kwargs)

        # Open the log for reading
        log = open(self.log.name, 'r')

        # Look for clues in the log
        for line in log.readlines():
            has_card = self.has_card_pt.match(line)
            is_driver_loaded = self.is_driver_loaded_pt.match(line)
            is_driver_enabled = self.is_driver_enabled_pt.match(line)

            single_card = self.single_card_pt.match(line)
            laptop = self.is_laptop_pt.match(line)

            no_change_stop = self.no_change_stop_pt.match(line)
            has_changed = self.has_changed_pt.match(line)

            removed_xorg = self.removed_xorg_pt.match(line)
            regenerated_xorg = self.regenerated_xorg_pt.match(line)
            not_modified_xorg = self.not_modified_xorg_pt.match(line)
            selected_driver = self.selected_driver_pt.match(line)
            no_action = self.no_action_pt.match(line)
            has_skipped_hybrid = self.has_skipped_hybrid_pt.match(line)

            # Detect the vendor
            if has_card:
                if has_card.group(1).strip().lower() == 'nvidia':
                    gpu_test.has_nvidia = (has_card.group(2).strip().lower() == 'yes')
                elif has_card.group(1).strip().lower() == 'intel':
                    gpu_test.has_intel = (has_card.group(2).strip().lower() == 'yes')
                elif has_card.group(1).strip().lower() == 'amd':
                    gpu_test.has_amd = (has_card.group(2).strip().lower() == 'yes')
            # Detect the kernel modules
            elif is_driver_loaded:
                if is_driver_loaded.group(1).strip().lower() == 'nouveau':
                    gpu_test.nouveau_loaded = (is_driver_loaded.group(2).strip().lower() == 'yes')
                elif is_driver_loaded.group(1).strip().lower() == 'nvidia':
                    gpu_test.nvidia_loaded = (is_driver_loaded.group(2).strip().lower() == 'yes')
                elif is_driver_loaded.group(1).strip().lower() == 'intel':
                    gpu_test.intel_loaded = (is_driver_loaded.group(2).strip().lower() == 'yes')
                elif is_driver_loaded.group(1).strip().lower() == 'radeon':
                    gpu_test.radeon_loaded = (is_driver_loaded.group(2).strip().lower() == 'yes')
                elif is_driver_loaded.group(1).strip().lower() == 'fglrx':
                    gpu_test.fglrx_loaded = (is_driver_loaded.group(2).strip().lower() == 'yes')
            # Detect the alternative
            elif is_driver_enabled:
                if is_driver_enabled.group(1).strip().lower() == 'nvidia':
                    gpu_test.nvidia_enabled = (is_driver_enabled.group(2).strip().lower() == 'yes')
                elif is_driver_enabled.group(1).strip().lower() == 'fglrx':
                    gpu_test.fglrx_enabled = (is_driver_enabled.group(2).strip().lower() == 'yes')
                elif is_driver_enabled.group(1).strip().lower() == 'mesa':
                    gpu_test.mesa_enabled = (is_driver_enabled.group(2).strip().lower() == 'yes')
                elif is_driver_enabled.group(1).strip().lower() == 'prime':
                    gpu_test.prime_enabled = (is_driver_enabled.group(2).strip().lower() == 'yes')
                elif is_driver_enabled.group(1).strip().lower() == 'pxpress':
                    gpu_test.pxpress_enabled = (is_driver_enabled.group(2).strip().lower() == 'yes')
            elif single_card:
                gpu_test.has_single_card = True
            elif laptop:
                if self.this_function_name == 'laptop_one_intel_one_amd_open':
                    print line
                    print laptop.group(1).strip().lower()
                gpu_test.is_laptop = (laptop.group(1).strip().lower() == 'yes')
            elif no_change_stop:
                gpu_test.has_changed = False
                gpu_test.has_not_acted = True
            elif has_changed:
                gpu_test.has_changed = True
            elif no_action:
                gpu_test.has_not_acted = True
            elif removed_xorg:
                gpu_test.has_removed_xorg = True
                # This is an action
                gpu_test.has_not_acted = False
            elif regenerated_xorg:
                gpu_test.has_regenerated_xorg = True
                # This is an action
                gpu_test.has_not_acted = False
            elif not_modified_xorg:
                gpu_test.has_removed_xorg = False
                gpu_test.has_regenerated_xorg = False
            elif selected_driver:
                gpu_test.has_selected_driver = True
                # This is an action
                gpu_test.has_not_acted = False
            elif has_skipped_hybrid:
                gpu_test.has_skipped_hybrid = True
                gpu_test.has_not_acted = True

        # Close the log
        log.close()



        '''
        for file in (self.last_boot_file,
                     self.new_boot_file,
                     self.fake_lspci,
                     self.fake_modules,
                     self.fake_alternatives,
                     self.log):
            target_dir = '/media/caviar4/data/ubuntu/gpu_manager/%s' % self.this_function_name
            try:
                file.close()
            except:
                pass
            try:
                os.mkdir(target_dir)
            except:
                pass
            try:
                shutil.copy(file.name, target_dir)
                os.unlink(file.name)
            except:
                print 'problem with', file.name
        '''



        return gpu_test

    def test_one_intel_no_change(self):
        '''intel -> intel'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('8086:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
i915-brw 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_changed=True,
                                   has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # No change
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No action
        self.assert_(gpu_test.has_not_acted)

    def test_one_nvidia_binary_no_change(self):
        '''nvidia -> nvidia'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('10de:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('10de:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_changed=True,
                                   has_not_acted=True)

        # Check the variables
        self.assert_(gpu_test.has_single_card)

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # No open!
        self.assertFalse(gpu_test.nouveau_loaded)
        # No change
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No action
        self.assert_(gpu_test.has_not_acted)

    def test_one_nvidia_open_no_change(self):
        '''nvidia (nouveau) -> nvidia (nouveau)'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('10de:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('10de:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
nouveau 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_changed=True,
                                   has_not_acted=True)

        # Check the variables
        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Open driver only!
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.mesa_enabled)
        # No change
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No action
        self.assert_(gpu_test.has_not_acted)

    def test_one_amd_binary_no_change(self):
        '''fglrx -> fglrx'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('1002:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('1002:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables
        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        # No radeon
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.nouveau_loaded)
        # No change
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No action
        self.assert_(gpu_test.has_not_acted)


        # What if the kernel module wasn't built
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables
        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        # No radeon
        self.assertFalse(gpu_test.radeon_loaded)
        # fglrx is not loaded
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.nouveau_loaded)
        # No change
        self.assertFalse(gpu_test.has_changed)
        # Select fallback and remove xorg.conf
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # Fallback action
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_amd_open_no_change(self):
        '''radeon -> radeon'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('1002:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('1002:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
radeon 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_changed=True,
                                   has_not_acted=True)

        # Check the variables
        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        # No fglrx
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.nouveau_loaded)
        # No change
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No action
        self.assert_(gpu_test.has_not_acted)

    def test_one_intel_to_nvidia_binary(self):
        '''intel -> nvidia'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('10de:28e8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        # We are going to enable nvidia
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # Action is required
        # We enable nvidia
        self.assertFalse(gpu_test.has_not_acted)


        # Let's try again, only this time it's all
        # already in place
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        # We are going to enable nvidia
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # Action is required
        # We enable nvidia
        self.assertFalse(gpu_test.has_not_acted)


        # What if the driver is enabled but the kernel
        # module is not there?
        #
        # The binary driver is not there
        # whereas the open driver is blacklisted
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        #The open driver is blacklisted
        self.assertFalse(gpu_test.nouveau_loaded)
        # No kenrel module
        self.assertFalse(gpu_test.nvidia_loaded)
        # The driver is enabled
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # We should switch to mesa
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_intel_to_nvidia_open(self):
        '''intel -> nouveau'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('10de:28e8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
nouveau 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assert_(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_intel_to_amd_open(self):
        '''intel -> radeon'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('1002:28e8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
radeon 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_intel_to_amd_binary(self):
        '''intel -> fglrx'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('1002:28e8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # We are going to enable fglrx
        self.assertFalse(gpu_test.fglrx_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # Action is required
        # We enable fglrx
        self.assertFalse(gpu_test.has_not_acted)


        # Let's try again, only this time it's all
        # already in place
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # We don't need to enable fglrx again
        self.assert_(gpu_test.fglrx_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # Action is not required
        self.assertFalse(gpu_test.has_not_acted)



        # What if the driver is enabled but the kernel
        # module is not there?
        #
        # The binary driver is not there
        # whereas the open driver is blacklisted
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        #The open driver is blacklisted
        self.assertFalse(gpu_test.radeon_loaded)
        # No kernel module
        self.assertFalse(gpu_test.fglrx_loaded)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.fglrx_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # We should switch to mesa
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_amd_open_to_intel(self):
        '''radeon -> intel'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('1002:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('8086:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # No need to do anything else
        self.assertFalse(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_amd_open_to_nvidia_open(self):
        '''radeon -> nouveau'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('1002:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('10de:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
nouveau 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assert_(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # No need to do anything else
        self.assertFalse(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


    def test_one_amd_open_to_nvidia_binary(self):
        '''radeon -> nouveau'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('1002:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('10de:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # Let's try again, only this time it's all
        # already in place

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # No need to do anything else
        self.assertFalse(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # What if the driver is enabled but the kernel
        # module is not there?
        #
        # The binary driver is not there
        # whereas the open driver is blacklisted
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        #The open driver is blacklisted
        self.assertFalse(gpu_test.nouveau_loaded)
        # No kenrel module
        self.assertFalse(gpu_test.nvidia_loaded)
        # The driver is enabled
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # We should switch to mesa
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_amd_binary_to_intel(self):
        '''fglrx -> intel'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('1002:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('8086:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        # User removed the discrete card without
        # uninstalling the binary driver
        # the kernel module is still loaded

        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
i915 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        # The binary driver is loaded and enabled
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # User removed the discrete card without
        # uninstalling the binary driver
        # the kernel module is no longer loaded
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        # The kernel module of the binary driver
        # is not loaded
        self.assertFalse(gpu_test.fglrx_loaded)
        # The binary driver is still enabled
        self.assert_(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_amd_binary_to_nvidia_open(self):
        '''fglrx -> nouveau'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('1002:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('10de:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        # User swapped the discrete card with
        # a discrete card from another vendor
        # without uninstalling the binary driver
        # the kernel module is still loaded

        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
nouveau 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        # The binary driver is loaded and enabled
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assert_(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # User swapped the discrete card with
        # a discrete card from another vendor
        # without uninstalling the binary driver
        # the kernel module is no longer loaded
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
nouveau 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        # The kernel module of the binary driver
        # is not loaded
        self.assertFalse(gpu_test.fglrx_loaded)
        # The binary driver is still enabled
        self.assert_(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assert_(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_amd_binary_to_nvidia_binary(self):
        '''fglrx -> nvidia'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('1002:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('10de:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        # User swapped the discrete card with
        # a discrete card from another vendor
        # and installed the new binary driver
        # however the kernel module wasn't built

        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
fake_alt 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # User swapped the discrete card with
        # a discrete card from another vendor
        # and installed the new binary driver
        # correctly
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # No need to select the driver
        self.assertFalse(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_amd_open_to_amd_binary(self):
        '''radeon -> fglrx'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('1002:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        # Same card
        self.fake_lspci.write('1002:28e8;0000:00:01:0;1')
        self.fake_lspci.close()

        # The module was built
        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
fake_alt 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assertFalse(gpu_test.has_selected_driver)
        self.assert_(gpu_test.has_not_acted)


        # Different card
        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('1002:2fe2;0000:00:01:0;1')
        self.fake_lspci.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        # We remove the xorg.conf
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assertFalse(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # What if the module was not built?

        # Same card
        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('1002:28e8;0000:00:01:0;1')
        self.fake_lspci.close()

        # The module was not built
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
fake_alt 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has not changed
        self.assertFalse(gpu_test.has_changed)
        # Move away xorg.conf if falling back
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver (fallback)
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # Different card
        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('1002:2fe2;0000:00:01:0;1')
        self.fake_lspci.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        # We remove the xorg.conf
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver (fallback)
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


    def test_one_nvidia_open_to_intel(self):
        '''nouveau -> intel'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('10de:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('8086:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)

        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_nvidia_open_to_amd_open(self):
        '''nouveau -> radeon'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('10de:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('1002:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules.write('''
radeon 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)

        # No AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_nvidia_open_to_amd_binary(self):
        '''nouveau -> fglrx'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('10de:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('1002:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        # No kernel module
        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # Mesa enabled
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)

        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # What if fglrx is enabled? (no kernel module)
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)

        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the fallback
        self.assert_(gpu_test.has_selected_driver)
        # Action is required
        self.assertFalse(gpu_test.has_not_acted)


        # What if kernel module is available and mesa is enabled?
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # Mesa enabled
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)

        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assert_(gpu_test.has_selected_driver)
        # Action is required
        self.assertFalse(gpu_test.has_not_acted)


        # What if kernel module is available and fglrx is enabled?
        # fglrx enabled
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assertFalse(gpu_test.mesa_enabled)

        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)

    def test_one_nvidia_binary_to_intel(self):
        '''nvidia -> intel'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('10de:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('8086:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        # Case 1: nvidia loaded and enabled

        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        # nvidia is still enabled
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # Action is required
        # We enable mesa
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2: nvidia loaded and not enabled
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        # nvidia is not enabled
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3: nvidia not loaded and enabled
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        # nvidia is still enabled
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 4: nvidia not loaded and not enabled
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        # nvidia is not enabled
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


    def test_one_nvidia_binary_to_amd_open(self):
        '''nvidia -> radeon'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('10de:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('1002:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        # Case 1: nvidia loaded and enabled

        self.fake_modules.write('''
radeon 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        # nvidia is still enabled
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # Action is required
        # We enable mesa
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2: nvidia loaded and not enabled
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        # nvidia is not enabled
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3: nvidia not loaded and enabled
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
radeon 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        # nvidia is still enabled
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 4: nvidia not loaded and not enabled
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
radeon 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)
        #No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        # nvidia is not enabled
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


    def test_one_nvidia_binary_to_amd_binary(self):
        '''nvidia -> fglrx'''
        self.this_function_name = sys._getframe().f_code.co_name
        self.last_boot_file.write('10de:28e8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('1002:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        # User swapped the discrete card with
        # a discrete card from another vendor
        # and installed the new binary driver
        # however the kernel module wasn't built

        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
fake_alt 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # User swapped the discrete card with
        # a discrete card from another vendor
        # and installed the new binary driver
        # correctly
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # No need to select the driver
        self.assertFalse(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # User swapped the discrete card with
        # a discrete card from another vendor
        # but did not install the new binary driver
        # The kernel module is still loaded.
        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
radeon 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver (fallback)
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)


        # User swapped the discrete card with
        # a discrete card from another vendor
        # but did not install the new binary driver
        # The kernel module is no longer loaded.

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
radeon 1447330 3 - Live 0x0000000000000000
fake_alt 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        # Select the driver (fallback)
        self.assert_(gpu_test.has_selected_driver)
        self.assertFalse(gpu_test.has_not_acted)

    def test_laptop_one_intel_one_amd_open(self):
        '''laptop: intel + radeon'''
        self.this_function_name = sys._getframe().f_code.co_name

        # Case 1: the discrete card is now available (BIOS)

        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
radeon 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2: the discrete card was already available (BIOS)
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has not changed
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No action is required
        self.assert_(gpu_test.has_not_acted)


        # Case 3: the discrete card is no longer available (BIOS)
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('8086:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)

    def test_desktop_one_intel_one_amd_open(self):
        '''desktop: intel + radeon'''
        self.this_function_name = sys._getframe().f_code.co_name

        # Case 1: the discrete card is now available (BIOS)
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
radeon 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2: the discrete card was already available (BIOS)
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assert_(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has not changed
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No action is required
        self.assert_(gpu_test.has_not_acted)


        # Case 3: the discrete card is no longer available (BIOS)
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('8086:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


    def test_laptop_one_intel_one_amd_binary(self):
        '''laptop: intel + fglrx'''
        self.this_function_name = sys._getframe().f_code.co_name

        # Case 1a: the discrete card is now available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1b: the discrete card is now available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1c: the discrete card is now available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1d: the discrete card is now available (BIOS)
        #          pxpress is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1e: the discrete card is now available (BIOS)
        #          pxpress is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1f: the discrete card is now available (BIOS)
        #          pxpress is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2a: the discrete card was already available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2b: the discrete card was already available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2c: the discrete card was already available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2d: the discrete card was already available (BIOS)
        #          pxpress is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2e: the discrete card was already available (BIOS)
        #          pxpress is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2f: the discrete card was already available (BIOS)
        #          pxpress is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 3a: the discrete card is no longer available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3b: the discrete card is no longer available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3c: the discrete card is no longer available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3d: the discrete card is no longer available (BIOS)
        #          pxpress is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3e: the discrete card is no longer available (BIOS)
        #          pxpress is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3f: the discrete card is no longer available (BIOS)
        #          pxpress is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


    def test_laptop_one_intel_one_nvidia_open(self):
        '''laptop: intel + nouveau'''
        self.this_function_name = sys._getframe().f_code.co_name

        # Case 1: the discrete card is now available (BIOS)

        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nouveau 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assert_(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2: the discrete card was already available (BIOS)
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assert_(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has not changed
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No action is required
        self.assert_(gpu_test.has_not_acted)


        # Case 3: the discrete card is no longer available (BIOS)
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('8086:68d8;0000:00:01:0;1')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is still enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


    def test_laptop_one_intel_one_nvidia_binary(self):
        '''laptop: intel + nvidia'''
        self.this_function_name = sys._getframe().f_code.co_name

        # Case 1a: the discrete card is now available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1b: the discrete card is now available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1c: the discrete card is now available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1d: the discrete card is now available (BIOS)
        #          prime is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1e: the discrete card is now available (BIOS)
        #          prime is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 1f: the discrete card is now available (BIOS)
        #          pxpress is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2a: the discrete card was already available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2b: the discrete card was already available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2c: the discrete card was already available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2d: the discrete card was already available (BIOS)
        #          pxpress is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2e: the discrete card was already available (BIOS)
        #          prime is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 2f: the discrete card was already available (BIOS)
        #          prime is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        '''
        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        '''
        # No further action is required
        self.assertTrue(gpu_test.has_not_acted)


        # Case 3a: the discrete card is no longer available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3b: the discrete card is no longer available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3c: the discrete card is no longer available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3d: the discrete card is no longer available (BIOS)
        #          prime is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3e: the discrete card is no longer available (BIOS)
        #          prime is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3f: the discrete card is no longer available (BIOS)
        #          pxpress is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative, is_laptop=True)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assert_(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


    def test_desktop_one_intel_one_nvidia_binary(self):
        '''desktop: intel + nvidia'''
        self.this_function_name = sys._getframe().f_code.co_name

        # Case 1a: the discrete card is now available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1b: the discrete card is now available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        # Has changed

        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertTrue(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1c: the discrete card is now available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed

        # Enable when we support hybrid laptops
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1d: the discrete card is now available (BIOS)
        #          prime is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1e: the discrete card is now available (BIOS)
        #          prime is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1f: the discrete card is now available (BIOS)
        #          pxpress is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('8086:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2a: the discrete card was already available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Remove xorg.conf
        self.remove_xorg_conf()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # See if it still regenerates xorg.conf if the
        # file is in place and correct
        self.xorg_file = open(self.xorg_file.name, 'w')
        self.xorg_file.write('''
Section "Device"
    Identifier "Default Card 1"
    BusID "PCI:1@0:0:0"
EndSection
''');
        self.xorg_file.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)

        # No further action is required
        self.assert_(gpu_test.has_not_acted)


        # See if it still regenerates xorg.conf if the
        # file is in place and incorrect
        self.xorg_file = open(self.xorg_file.name, 'w')
        self.xorg_file.write('''
Section "Device"
    Identifier "Default Card 1"
    Driver "fglrx"
    BusID "PCI:1@0:0:0"
EndSection
''');
        self.xorg_file.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2b: the discrete card was already available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2c: the discrete card was already available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2d: the discrete card was already available (BIOS)
        #          prime is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2e: the discrete card was already available (BIOS)
        #          prime is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # NVIDIA
        self.assert_(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2f: the discrete card was already available (BIOS)
        #          prime is not enabled but the module is loaded



        # Case 3a: the discrete card is no longer available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3b: the discrete card is no longer available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assert_(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3c: the discrete card is no longer available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3d: the discrete card is no longer available (BIOS)
        #          prime is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3e: the discrete card is no longer available (BIOS)
        #          prime is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/nvidia-331-updates-prime/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assert_(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3f: the discrete card is no longer available (BIOS)
        #          pxpress is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
8086:68d8;0000:00:01:0;1
10de:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
8086:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
i915 1447330 3 - Live 0x0000000000000000
nvidia 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/nvidia-331-updates/ld.so.conf
/usr/lib/nvidia-331-updates-prime/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # Intel
        self.assert_(gpu_test.has_intel)
        self.assert_(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assertFalse(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assert_(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)

    def test_desktop_one_amd_one_amd(self):
        '''Multiple AMD GPUs'''
        self.this_function_name = sys._getframe().f_code.co_name

        # Case 1a: the discrete card is now available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file.write('1002:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1b: the discrete card is now available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('1002:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
old_fake 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertTrue(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1c: the discrete card is now available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('1002:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # No AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        # Has changed

        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1d: the discrete card is now available (BIOS)
        #          pxpress is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('1002:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1e: the discrete card is now available (BIOS)
        #          pxpress is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('1002:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 1f: the discrete card is now available (BIOS)
        #          pxpress is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('1002:68d8;0000:00:01:0;1')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2a: the discrete card was already available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fglrx 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # See if it still regenerates xorg.conf if the
        # file is in place and correct
        self.xorg_file = open(self.xorg_file.name, 'w')
        self.xorg_file.write('''
Section "Device"
    Identifier "Default Card 1"
    BusID "PCI:1@0:0:0"
EndSection

Section "Device"
    Identifier "Default Card 1"
    BusID "PCI:0@0:1:0"
EndSection
''');
        self.xorg_file.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assertFalse(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)

        # No further action is required
        self.assert_(gpu_test.has_not_acted)


        # See if it still regenerates xorg.conf if the
        # file is in place and incorrect
        self.xorg_file = open(self.xorg_file.name, 'w')
        self.xorg_file.write('''
Section "Device"
    Identifier "Default Card 1"
    Driver "fglrx"
    BusID "PCI:1@0:0:0"
EndSection
''');
        self.xorg_file.close()

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars()

        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2b: the discrete card was already available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2c: the discrete card was already available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2d: the discrete card was already available (BIOS)
        #          pxpress is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assert_(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2e: the discrete card was already available (BIOS)
        #          pxpress is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assertFalse(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assertFalse(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)

        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 2f: the discrete card was already available (BIOS)
        #          pxpress is not enabled but the module is loaded



        # Case 3a: the discrete card is no longer available (BIOS)
        #          the driver is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assertFalse(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3b: the discrete card is no longer available (BIOS)
        #          the driver is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/fglrx/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assert_(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3c: the discrete card is no longer available (BIOS)
        #          the driver is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3d: the discrete card is no longer available (BIOS)
        #          pxpress is enabled and the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3e: the discrete card is no longer available (BIOS)
        #          pxpress is enabled but the module is not loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fake 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/pxpress/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is not enabled
        self.assertFalse(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assertFalse(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assert_(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)


        # Case 3f: the discrete card is no longer available (BIOS)
        #          pxpress is not enabled but the module is loaded
        self.last_boot_file = open(self.last_boot_file.name, 'w')
        self.last_boot_file.write('''
1002:68d8;0000:00:01:0;1
1002:28e8;0000:01:00:0;0''')
        self.last_boot_file.close()

        self.fake_lspci = open(self.fake_lspci.name, 'w')
        self.fake_lspci.write('''
1002:68d8;0000:00:01:0;1
''')
        self.fake_lspci.close()

        self.fake_modules = open(self.fake_modules.name, 'w')
        self.fake_modules.write('''
fake_old 1447330 3 - Live 0x0000000000000000
fglrx 1447330 3 - Live 0x0000000000000000
''')
        self.fake_modules.close()

        self.fake_alternatives = open(self.fake_alternatives.name, 'w')
        self.fake_alternatives.write('''
/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf
/usr/lib/fglrx/ld.so.conf
/usr/lib/pxpress/ld.so.conf
''')
        self.fake_alternatives.close()

        # The alternative in use
        fake_alternative = '/usr/lib/x86_64-linux-gnu/mesa/ld.so.conf'

        # Call the program
        self.exec_manager(fake_alternative)

        # Collect data
        gpu_test = self.check_vars(has_not_acted=True)

        # Check the variables

        # Check if laptop
        self.assertFalse(gpu_test.is_laptop)

        self.assert_(gpu_test.has_single_card)

        # No Intel
        self.assertFalse(gpu_test.has_intel)
        self.assertFalse(gpu_test.intel_loaded)

        # Mesa is enabled
        self.assert_(gpu_test.mesa_enabled)
        # AMD
        self.assert_(gpu_test.has_amd)
        self.assertFalse(gpu_test.radeon_loaded)
        self.assert_(gpu_test.fglrx_loaded)
        self.assertFalse(gpu_test.fglrx_enabled)
        self.assertFalse(gpu_test.pxpress_enabled)
        # No NVIDIA
        self.assertFalse(gpu_test.has_nvidia)
        self.assertFalse(gpu_test.nouveau_loaded)
        self.assertFalse(gpu_test.nvidia_loaded)
        self.assertFalse(gpu_test.nvidia_enabled)
        self.assertFalse(gpu_test.prime_enabled)
        # Has changed
        self.assert_(gpu_test.has_changed)
        self.assert_(gpu_test.has_removed_xorg)
        self.assertFalse(gpu_test.has_regenerated_xorg)
        self.assert_(gpu_test.has_selected_driver)
        # No further action is required
        self.assertFalse(gpu_test.has_not_acted)



if __name__ == '__main__':
    unittest.main()
