import pytest
from pricing import quote

@pytest.mark.parametrize('price,fee',[(9999,599),(10000,0),(10001,0)])
def test_free_shipping_boundary(line_factory,price,fee):
    result=quote([line_factory(unit_cents=price)])
    assert result=={'subtotal_cents':price,'shipping_cents':fee,'total_cents':price+fee}


def test_discount_changes_shipping_eligibility(line_factory):
    assert quote([line_factory()],100)=={'subtotal_cents':9900,'shipping_cents':599,'total_cents':10499}


def test_round_down_after_discount(line_factory):
    assert quote([line_factory(unit_cents=101)],5000)['subtotal_cents']==50


def test_multiple_lines_and_no_input_mutation(line_factory):
    lines=[line_factory(quantity=2,unit_cents=3000),line_factory(unit_cents=4000)]
    before=list(lines)
    assert quote(lines)['total_cents']==10000
    assert lines==before

@pytest.mark.parametrize('bps',[-1,10001,True,1.5])
def test_invalid_discount(line_factory,bps):
    with pytest.raises(ValueError,match='discount'):quote([line_factory()],bps)

@pytest.mark.parametrize('fields',[{'sku':''},{'quantity':0},{'quantity':True},{'quantity':1.5},
                                  {'unit_cents':-1},{'unit_cents':True}])
def test_invalid_line(line_factory,fields):
    with pytest.raises(ValueError):quote([line_factory(**fields)])


def test_empty_lines():
    with pytest.raises(ValueError,match='at least'):quote([])
