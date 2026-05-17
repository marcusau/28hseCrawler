import asyncio
from dataclasses import dataclass, asdict
from typing import Optional, List
from scrapling.fetchers import FetcherSession


@dataclass
class PropertyDetail:
    """Data class for 28hse property detail information."""
    property_id: str
    agent_property_id: Optional[str] = None
    price: Optional[str] = None
    monthly_mortgage: Optional[str] = None
    building_area: Optional[str] = None
    saleable_area: Optional[str] = None
    district_building: Optional[str] = None
    orientation: Optional[str] = None
    floor_level: Optional[str] = None
    rooms: Optional[str] = None
    kitchen_type: Optional[str] = None
    cooking_mode: Optional[str] = None
    primary_school_net: Optional[str] = None
    secondary_school_net: Optional[str] = None
    address: Optional[str] = None
    agent_company: Optional[str] = None
    agent_name: Optional[str] = None
    title: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


async def scrape_property_detail(url: str) -> PropertyDetail:
    """
    Scrape property detail data from a 28hse property page.

    Args:
        url: The URL of the property detail page (e.g., 'https://www.28hse.com/buy/apartment/property-3843066')

    Returns:
        A PropertyDetail dataclass containing extracted property data
    """
    async with FetcherSession(
        impersonate="safari",
        http3=False,
        stealthy_headers=True,
        timeout=30,
        retries=3
    ) as session:
        page = await session.get(url, stealthy_headers=True)

        # Extract property data using correct selectors
        property_id = url.split('property-')[-1]
        mortgage_elements = page.css('table.ui.table.tablePair tr')

        def extract_row_value(label_text: str) -> Optional[str]:
            for row in mortgage_elements:
                label = row.css('td.table_left::text').get()
                if label and label_text in label:
                    value = row.css('td.table_right .pairValue::text').get()
                    return value.strip() if value else None
            return None

        # Address has a different selector (table_right.last)
        address = None
        for row in mortgage_elements:
            label = row.css('td.table_left::text').get()
            if label and '物業地址' in label:
                value = row.css('td.table_right.last .pairValue::text').get()
                address = value.strip() if value else None
                break

        # Helper to safely get and strip
        def safe_strip(selector: str) -> Optional[str]:
            val = page.css(selector).get()
            return val.strip() if val else None

        return PropertyDetail(
            property_id=property_id,
            agent_property_id=safe_strip('.sub.header:contains("物業編號")::text'),
            price=safe_strip('td.table_right .pairValue.price.red::text'),
            monthly_mortgage=extract_row_value('按揭每月供款'),
            building_area=extract_row_value('建築面積'),
            saleable_area=extract_row_value('實用面積'),
            district_building=extract_row_value('地區屋苑'),
            orientation=extract_row_value('座向'),
            floor_level=extract_row_value('單位樓層'),
            rooms=extract_row_value('房間及浴室'),
            kitchen_type=extract_row_value('廚房類型'),
            cooking_mode=extract_row_value('廚房煮食模式'),
            primary_school_net=safe_strip('td.table_right .pairSubValue_novalue a::text'),
            secondary_school_net=safe_strip('td.table_right .pairSubValue_novalue::text'),
            address=address,
            agent_company=safe_strip('.content_body_outer a[href*="agent/"]::text'),
            agent_name=safe_strip('.contactsHeader + h4.ui.header::text'),
            title=safe_strip('h1::text'),
        )


async def scrape_property_details_batch(urls: List[str]) -> List[PropertyDetail]:
    """
    Scrape multiple property detail pages concurrently.

    Args:
        urls: List of property detail page URLs

    Returns:
        List of PropertyDetail dataclasses
    """
    async with FetcherSession(
        impersonate="safari",
        http3=False,
        stealthy_headers=True,
        timeout=30,
        retries=3
    ) as session:
        tasks = [scrape_property_detail(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, PropertyDetail)]


# Example usage
if __name__ == '__main__':

        # Example: Batch scraping multiple URLs
        urls = [
            'https://www.28hse.com/buy/apartment/property-3843066',
            'https://www.28hse.com/buy/apartment/property-3843065',
            # Add more URLs here
        ]
        results = asyncio.run(scrape_property_details_batch(urls))
        print(f"Scraped {len(results)} properties")
        for prop in results:

            # Print results
            print("Property Data:")
            for key, value in prop.to_dict().items():
                print(f"  {key}: {value}")