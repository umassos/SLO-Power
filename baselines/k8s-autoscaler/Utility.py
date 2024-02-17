class Utility():       
    def convert_from_microwatt_to_watt(self, power_value):
        # return float("{:.2f}".format(power_value / 1000000))
        return round(power_value / 1000000, 2)
    
    def convert_from_watt_to_microwatt(self, power_value):
        return power_value * 1000000

    def convert_from_millisecond_to_second(self, time_value):
        # return float("{:.2f}".format(time_value / 1000))
        return round(time_value / 1000, 2)

    def convert_from_second_to_millisecond(self, time_value):
        return time_value * 1000