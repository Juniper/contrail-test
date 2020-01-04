import sys
import psutil

class ProcessStatus:

    output_dict={}    
    process_name = sys.argv[1]       

    def get_process_status (self, process_name):

        for proc in psutil.process_iter():
            if proc.name() == process_name:
                cpu_percent= proc.cpu_percent(interval=3)  
                memory_percent= proc.memory_percent()
                rss= proc.memory_info().rss
                vms= proc.memory_info().vms
                self.output_dict= {'cpu_percent': cpu_percent,
                                   'memory_percent': round (memory_percent,2),
                                   'rss': str(rss/ float(2 ** 20))+'mb',
                                   'vms': str(vms/ float(2 ** 20))+'mb',
                                   }
        return self.output_dict

if __name__ == "__main__":
    status = ProcessStatus()
    sys.exit(status.get_process_status(sys.argv[1]))
