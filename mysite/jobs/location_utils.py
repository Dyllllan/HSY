"""
地点解析工具模块
用于从location字段中提取省市区信息
"""
import re

# 中国省份列表
PROVINCES = [
    '北京', '上海', '天津', '重庆',
    '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
    '江苏', '浙江', '安徽', '福建', '江西', '山东',
    '河南', '湖北', '湖南', '广东', '广西', '海南',
    '四川', '贵州', '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆',
    '香港', '澳门', '台湾'
]

# 直辖市和特别行政区
DIRECTLY_GOVERNED_CITIES = ['北京', '上海', '天津', '重庆', '香港', '澳门']


def parse_location(location_str):
    """
    解析地点字符串，提取省市区信息
    
    支持格式：
    - "北京-朝阳区"
    - "北京市朝阳区"
    - "上海-浦东新区"
    - "广东省深圳市南山区"
    - "北京" (只有省份)
    
    返回: (province, city, district)
    """
    if not location_str:
        return None, None, None
    
    location_str = location_str.strip()
    
    # 初始化
    province = None
    city = None
    district = None
    
    # 尝试匹配省份
    for p in PROVINCES:
        if location_str.startswith(p):
            province = p
            location_str = location_str[len(p):].strip()
            break
    
    # 如果没有找到省份，尝试从常见格式中提取
    if not province:
        # 匹配格式：XX省/市/自治区
        province_match = re.match(r'^([^省市区县]+?)(?:省|市|自治区|特别行政区)', location_str)
        if province_match:
            province = province_match.group(1)
            location_str = location_str[len(province_match.group(0)):].strip()
    
    # 处理分隔符（-、/、|、空格等）
    parts = re.split(r'[-/|、\s]+', location_str)
    parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 0]
    
    # 如果还有剩余部分，尝试提取市和区
    if parts:
        # 第一个部分通常是市
        if parts[0] and not re.match(r'^[区县]$', parts[0]):
            # 移除"市"后缀
            potential_city = parts[0].replace('市', '').replace('省', '')
            if potential_city != parts[0]:  # 如果移除了"市"或"省"，说明确实是城市
                city = potential_city
            elif len(parts) > 1:  # 如果没有"市"后缀，但后面还有区县，则可能是城市名
                city = parts[0]
            elif not re.search(r'[区县]', parts[0]):  # 如果包含区县关键字，则不是城市
                city = parts[0]
        
        # 第二个部分通常是区/县
        if len(parts) > 1:
            district = parts[1].replace('区', '').replace('县', '').replace('市', '')
        elif len(parts) == 1 and parts[0]:
            # 如果只有一个部分，检查是否是区县名
            if re.search(r'[区县]', parts[0]):
                district = parts[0].replace('区', '').replace('县', '').replace('市', '')
            elif not city and not re.search(r'[省]', parts[0]):
                # 如果还没有city，且不包含"省"，可能是城市名
                city = parts[0]
    
    # 对于直辖市，如果没有找到city，将province作为city
    if province in DIRECTLY_GOVERNED_CITIES and not city:
        city = province
    
    # 清理结果：移除空字符串
    province = province if province else None
    city = city if city else None
    district = district if district else None
    
    return province, city, district


def extract_provinces_from_jobs():
    """从所有职位中提取唯一的省份列表"""
    from .models import JobPage
    
    provinces = set()
    for job in JobPage.objects.live().values_list('location', flat=True):
        if job:
            province, _, _ = parse_location(job)
            if province:
                provinces.add(province)
    
    return sorted(list(provinces))


def extract_cities_from_jobs(province=None):
    """从所有职位中提取唯一的城市列表"""
    from .models import JobPage
    
    cities = set()
    for job in JobPage.objects.live().values_list('location', flat=True):
        if job:
            p, city, _ = parse_location(job)
            if city:
                if province:
                    if p == province:
                        cities.add(city)
                else:
                    cities.add(city)
    
    return sorted(list(cities))


def extract_districts_from_jobs(province=None, city=None):
    """从所有职位中提取唯一的区县列表"""
    from .models import JobPage
    
    districts = set()
    for job in JobPage.objects.live().values_list('location', flat=True):
        if job:
            p, c, district = parse_location(job)
            if district:
                if province and city:
                    if p == province and c == city:
                        districts.add(district)
                elif province:
                    if p == province:
                        districts.add(district)
                elif city:
                    if c == city:
                        districts.add(district)
                else:
                    districts.add(district)
    
    return sorted(list(districts))
