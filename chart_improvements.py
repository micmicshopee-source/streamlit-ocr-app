"""
图表设计改进代码
基于 Google Material Design 3.0 原则
"""

# Google Material Design 配色方案
GOOGLE_COLORS = {
    'primary': '#4285F4',      # Google Blue
    'secondary': '#34A853',    # Google Green
    'accent': '#FBBC04',       # Google Yellow
    'error': '#EA4335',        # Google Red
    'purple': '#9C27B0',       # Material Purple
    'orange': '#FF9800',       # Material Orange
    'teal': '#009688',         # Material Teal
    'pink': '#E91E63',         # Material Pink
    'cyan': '#00BCD4',         # Material Cyan
    'indigo': '#3F51B5',       # Material Indigo
}

# 图表配色方案（按顺序使用）
CHART_COLOR_SCHEME = [
    '#4285F4',  # Blue
    '#34A853',  # Green
    '#FBBC04',  # Yellow
    '#EA4335',  # Red
    '#9C27B0',  # Purple
    '#FF9800',  # Orange
    '#009688',  # Teal
    '#E91E63',  # Pink
    '#00BCD4',  # Cyan
    '#3F51B5',  # Indigo
]

# 图表配置常量
CHART_HEIGHT = 280
CHART_PADDING = 20
CHART_BACKGROUND = 'transparent'

def create_pie_chart(df, category_col, value_col='count()', title="分布图"):
    """
    创建改进的圆饼图
    
    参数:
        df: DataFrame
        category_col: 分类列名
        value_col: 数值列名或聚合函数
        title: 图表标题
    """
    import altair as alt
    
    # 获取唯一分类数量
    unique_categories = df[category_col].nunique()
    color_range = CHART_COLOR_SCHEME[:unique_categories]
    
    chart = alt.Chart(df).mark_arc(
        innerRadius=40,  # 增大内径，更现代化
        outerRadius=100,
        stroke='#1E1E1E',
        strokeWidth=2
    ).encode(
        theta=alt.Theta(value_col, type="quantitative"),
        color=alt.Color(
            category_col, 
            type="nominal",
            scale=alt.Scale(range=color_range),
            legend=alt.Legend(
                title=category_col,
                titleFontSize=12,
                labelFontSize=11,
                titleColor='#FFFFFF',
                labelColor='#C4C4C4',
                orient='right',
                padding=10
            )
        ),
        tooltip=[
            alt.Tooltip(category_col, title="类别"),
            alt.Tooltip(value_col, title="数量", format=',.0f')
        ]
    ).properties(
        height=CHART_HEIGHT,
        width=CHART_HEIGHT,
        background=CHART_BACKGROUND,
        padding=CHART_PADDING
    )
    
    return chart

def create_line_chart(df, x_col, y_col, title="趋势图", color=None):
    """
    创建改进的折线图
    
    参数:
        df: DataFrame
        x_col: X轴列名
        y_col: Y轴列名
        title: 图表标题
        color: 线条颜色（默认使用 Google Blue）
    """
    import altair as alt
    
    if color is None:
        color = GOOGLE_COLORS['primary']
    
    chart = alt.Chart(df).mark_line(
        point=alt.OverlayMarkDef(
            filled=True,
            size=60,
            stroke='#1E1E1E',
            strokeWidth=2
        ),
        strokeWidth=3,
        strokeCap='round',
        strokeJoin='round',
        color=color
    ).encode(
        x=alt.X(
            f'{x_col}:T' if 'date' in x_col.lower() or '日期' in x_col else f'{x_col}:N',
            title=x_col,
            axis=alt.Axis(
                format='%Y/%m/%d' if 'date' in x_col.lower() or '日期' in x_col else None,
                labelFontSize=11,
                titleFontSize=12,
                labelColor='#C4C4C4',
                titleColor='#FFFFFF',
                gridColor='#2D2D2D',
                domainColor='#3D3D3D',
                tickColor='#3D3D3D'
            )
        ),
        y=alt.Y(
            f'{y_col}:Q',
            title=y_col,
            axis=alt.Axis(
                format='$,.0f' if '$' in str(y_col) or '金额' in str(y_col) or '總計' in str(y_col) else ',.0f',
                labelFontSize=11,
                titleFontSize=12,
                labelColor='#C4C4C4',
                titleColor='#FFFFFF',
                gridColor='#2D2D2D',
                domainColor='#3D3D3D'
            )
        ),
        tooltip=[
            alt.Tooltip(f'{x_col}:T' if 'date' in x_col.lower() or '日期' in x_col else f'{x_col}:N', 
                       format='%Y年%m月%d日' if 'date' in x_col.lower() or '日期' in x_col else None,
                       title=x_col),
            alt.Tooltip(f'{y_col}:Q', 
                       format='$,.0f' if '$' in str(y_col) or '金额' in str(y_col) or '總計' in str(y_col) else ',.0f',
                       title=y_col)
        ]
    ).properties(
        height=CHART_HEIGHT,
        background=CHART_BACKGROUND,
        padding=CHART_PADDING
    )
    
    return chart

def create_bar_chart(df, x_col, y_col, title="柱状图", color_scheme='gradient'):
    """
    创建改进的柱状图
    
    参数:
        df: DataFrame
        x_col: X轴列名
        y_col: Y轴列名
        title: 图表标题
        color_scheme: 配色方案 ('gradient' 或 'categorical')
    """
    import altair as alt
    
    if color_scheme == 'gradient':
        # 使用渐变配色
        color_encoding = alt.Color(
            f'{y_col}:Q',
            scale=alt.Scale(
                range=['#4285F4', '#8AB4F8'],  # 蓝色渐变
                domain=[df[y_col].min(), df[y_col].max()]
            ),
            legend=None
        )
    else:
        # 使用分类配色
        unique_values = df[x_col].nunique()
        color_range = CHART_COLOR_SCHEME[:unique_values]
        color_encoding = alt.Color(
            f'{x_col}:N',
            scale=alt.Scale(range=color_range),
            legend=None
        )
    
    chart = alt.Chart(df).mark_bar(
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4,
        stroke='#1E1E1E',
        strokeWidth=1
    ).encode(
        x=alt.X(
            f'{x_col}:N',
            title=x_col,
            sort='-y',
            axis=alt.Axis(
                labelAngle=-45,
                labelFontSize=11,
                titleFontSize=12,
                labelColor='#C4C4C4',
                titleColor='#FFFFFF',
                domainColor='#3D3D3D'
            )
        ),
        y=alt.Y(
            f'{y_col}:Q',
            title=y_col,
            axis=alt.Axis(
                labelFontSize=11,
                titleFontSize=12,
                labelColor='#C4C4C4',
                titleColor='#FFFFFF',
                gridColor='#2D2D2D',
                domainColor='#3D3D3D'
            )
        ),
        color=color_encoding,
        tooltip=[
            alt.Tooltip(x_col, title="类别"),
            alt.Tooltip(f'{y_col}:Q', title="数量", format=',.0f')
        ]
    ).properties(
        height=CHART_HEIGHT,
        background=CHART_BACKGROUND,
        padding=CHART_PADDING
    )
    
    return chart

def create_chart_title(title, icon="📊"):
    """
    创建统一的图表标题样式
    
    参数:
        title: 标题文字
        icon: 图标（emoji）
    """
    return f"""
    <div style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="font-size: 20px; margin-right: 8px;">{icon}</span>
        <h3 style="margin: 0; font-size: 18px; font-weight: 600; color: #FFFFFF;">{title}</h3>
    </div>
    """
