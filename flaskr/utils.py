def validate_update_frequency(update_frequency: str) -> tuple[int, str]:
    try:
        # 分割字符串，提取数值和单位
        parts = update_frequency.split()
        if len(parts) != 2:
            raise ValueError("update_frequency must be in the format '<number> <unit>' (e.g., '1 minute').")

        value = int(parts[0])  # 提取数值
        unit = parts[1].lower()  # 提取单位并转换为小写

        # 校验单位是否有效
        valid_units = ['second', 'seconds', 'minute', 'minutes', 'hour', 'hours', 'day', 'days', 'week', 'weeks']
        if unit not in valid_units:
            raise ValueError(f"Invalid unit: {unit}. Supported units are: {valid_units}.")

        # 校验数值是否为正整数
        if value <= 0:
            raise ValueError(f"Invalid value: {value}. Value must be a positive integer.")

        return value, unit
    except ValueError as e:
        raise ValueError(f"Invalid update_frequency: {update_frequency}. {str(e)}")