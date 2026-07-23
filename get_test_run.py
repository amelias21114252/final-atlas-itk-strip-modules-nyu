#!/usr/bin/env python
#python get_test_run.py --serial_number 20USBHX2002592 --test_name 'Response Curve TC'
#python get_test_run.py --serial_number 20USBML1235274 --test_name 'Module AMAC IV TC'


#!/usr/bin/env python
import argparse
import os
from pprint import pprint
# https://itkdb.docs.cern.ch/latest/
import itkdb

def get_test_run(serial_number="20USBHX2002592", test_name='Response Curve TC'):
    '''
    Following this example:
    https://itkdb.docs.cern.ch/latest/examples/#retrieve-a-test-run

    Athenticate following these instructions by copying token to environment variable: 
      export ITK_DB_AUTH=TOKEN 
    https://gitlab.cern.ch/atlas-itk/sw/db/production_database_scripts/-/tree/master?ref_type=heads#authentication
    '''
    token = os.getenv("ITK_DB_AUTH")
    user = itkdb.core.UserBearer(bearer=token)
    client = itkdb.Client(user=user)  

    component = client.get("getComponent", json={"component": serial_number})  

    testID = [
        y["id"]
        for x in component["tests"]
        for y in x["testRuns"]
        if x["name"] == test_name
    ]  
    print('Serial number: {0}'.format(serial_number))
    print('Test name: {0}'.format(test_name))
    print('Getting test ID: {0}'.format(testID))
    testRun = client.get("getTestRun", json={"testRun": testID[0]})  

    # Results of tests and print them out
    for x in testRun['results']:
      # Find the merged lists of input noise under results
      if x['name'] == 'innse_under':
        innse_under = x['value']
        print('Input noise under:')
        pprint(innse_under)
      # Find the merged lists of input noise away results
      if x['name'] == 'innse_away':
        innse_away = x['value']
        print('Input noise away:')
        pprint(innse_away)
      if x['code'] == 'CURRENT':
        print('IV currents')
        current = x['value']
        pprint(current)
      if x['code'] == 'VOLTAGE':
        print('IV voltages')
        voltage = x['value']
        pprint(voltage)

    # General component information 
    print('-------------------------------------------')
    print('Full component information:')
    print('-------------------------------------------')
    pprint(testRun['components'])

    # Get the AMAC negative-temperature-coefficient (NTC) temperature
    amac_ntcpb = testRun['properties'][0]['value']['AMAC_NTCpb'] # Powerboard
    amac_ntcx  = testRun['properties'][0]['value']['AMAC_NTCx']  # Hybrid X
    amac_ntcy  = testRun['properties'][0]['value']['AMAC_NTCy']  # Hybrid Y (SS only)
    print('-------------------------------------------')
    print('AMAC temperature information')
    print('-------------------------------------------')
    print('AMAC NTC PB: ')
    pprint(amac_ntcpb)
    print('AMAC NTC HyX:')
    pprint(amac_ntcx)

    # Get parent name (module serial number) if hybrid
    if 'HX' in serial_number or 'HY' in serial_number:
      parent_name = testRun['components'][0]['ancestorMap']['parent']['component']['serialNumber']
      print('Module (parent) serial number: {0}'.format(parent_name))

    # Get child name (hybrid serial number) if module
    if 'ML' in serial_number or 'MS' in serial_number:
      child_name = testRun['properties'][1]['value']['name'] 
      print('Hybrid (child) serial number: {0}'.format(child_name))

    print('-------------------------------------------')
    print('Finished querying ITk database for following test:')
    print('-------------------------------------------')
    print('Serial number: {0}'.format(serial_number))
    print('Test name: {0}'.format(test_name))
    print('Getting test ID: {0}'.format(testID))
    
    timestamp = testRun['components'][0]['stateTs']
    print('Timestamp: {0}'.format(timestamp))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read from production database")
    parser.add_argument("--serial_number", help="Serial number e.g. 20USBHX2002592")
    parser.add_argument("--test_name", help="Name of test e.g. 'Response Curve TC' ")

    args = parser.parse_args()
    
    serial_number = '20USBHX2002592'
    test_name     = 'Response Curve TC'
    if args.serial_number is not None:
      serial_number = args.serial_number
    if args.serial_number is not None:
      test_name = args.test_name
    
    get_test_run(serial_number, test_name)
